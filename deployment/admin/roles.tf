# Custom roles rather than predefined ones. roles/storage.admin and
# roles/discoveryengine.editor are far broader than any persona here needs, and
# neither can express "create but never delete" -- which is the whole point of the
# maintainer/reaper split. Every permission below was confirmed grantable in a custom
# role via iam.permissions.queryTestablePermissions; a name the API does not accept
# fails the apply outright.
#
# lifecycle.prevent_destroy on each: deleting a custom role blocks reuse of its
# role_id for thirty days, so an accidental destroy is not something to discover
# during an incident.
#
# The three human roles are layers, not bundles. tfaContributor is the base every
# person holds, and tfaCorpusMaintainer and tfaCorpusAdmin each carry only what they
# add on top of it -- so a maintainer holds two roles and reads the corpus through the
# contributor one. IAM allow policies are additive, so the effective permission set is
# the union, and `mise run //deployment:grant` binds the whole stack in one command.
#
# Layering rather than self-contained roles because tfaCorpusAdmin is meant to be held
# briefly and then removed. Peeling off one layer leaves the person exactly as they
# were; revoking a self-contained superset would strip their ordinary access with it,
# which makes handing back a break-glass role something to put off.
#
# tfaReaper is the exception and is deliberately complete on its own. It belongs to a
# service account that holds nothing else, and it must not inherit permissions from a
# role meant for people.

resource "google_project_iam_custom_role" "contributor" {
  role_id     = "tfaContributor"
  title       = "Tenant First Aid contributor"
  description = "Run the app and evaluations locally. Read only: cannot create or delete anything."
  stage       = "GA"

  permissions = [
    # Query the corpus the way the deployed app does.
    "discoveryengine.servingConfigs.search",
    # Read a datastore's billing_estimation to decide whether it was reindexed
    # since an experiment ran. Only `langsmith-dataset runs stopgap-check` needs
    # this, and it swallows the failure, so a contributor missing the permission
    # sees no error -- just a redundant live re-query on every invocation.
    "discoveryengine.dataStores.get",
    #
    # dataStores.list is deliberately absent. This role holds no create permission,
    # so every corpus a contributor can use is one somebody else made, and there are
    # only two: the promoted one an environment serves, named in
    # deployment/envs/<env>/datastore_ids.auto.tfvars.json and readable from a clone
    # with no GCP access at all; or a scratch generation a maintainer provisioned, in
    # which case the maintainer passes on the ID that create-datastore-gcs printed.
    # Neither route enumerates. Listing would also be worse than useless here: the
    # project holds several obsolete datastores and the listing marks none of them, so
    # it invites a contributor to evaluate against the wrong corpus -- wrong in the
    # silent direction.
    #
    # Call the model. The app talks to Gemini through Vertex AI.
    "aiplatform.endpoints.predict",
    # User credentials carry no project of their own, so every call is attributed
    # to a billing project via x-goog-user-project -- and that attribution is
    # itself an authorization check. Without this, requests fail with
    # USER_PROJECT_DENIED before reaching the API being called. Service accounts
    # self-attribute and never need it, which is why it is easy to miss.
    "serviceusage.services.use",
    # See the corpus inventory: `list-artifacts`. Buckets and their labels only --
    # names, owner and lease -- never object contents, so this adds no read on the
    # state bucket or on any corpus document. That distinction is why the pair is
    # split across two roles rather than granted together: reading each artifact's
    # manifest needs storage.objects.get, which a custom role cannot scope to the
    # corpus buckets, so at project level it would also read OpenTofu state.
    # list_artifacts degrades instead, and prints the inventory without the
    # per-artifact datastore lines.
    #
    # Contributors get this because knowing which scratch artifacts exist, who owns
    # one and whether it has lapsed is the information needed to ask a maintainer
    # for the right thing -- and there is no reason to make it privileged.
    "storage.buckets.list",
  ]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_custom_role" "corpus_maintainer" {
  role_id     = "tfaCorpusMaintainer"
  title       = "Tenant First Aid corpus maintainer"
  description = "Adds building and promoting corpus artifacts to tfaContributor. Deliberately cannot delete: that belongs to the reaper."
  stage       = "GA"

  permissions = [
    # Layered on tfaContributor, which supplies reading and querying the corpus and
    # the quota attribution every user credential needs.
    #
    # Build an artifact: a bucket of documents, a datastore imported from it, an app.
    "storage.buckets.create",
    "storage.buckets.get",
    "storage.objects.create",
    # At project level this also reads OpenTofu state, including the state for
    # deployment/envs/* once those land, which is likely to record provider-recorded
    # secrets. A custom role cannot scope a single permission to "corpus buckets only" --
    # there is no naming convention that distinguishes them from the state bucket, and
    # this role mixes storage.* with discoveryengine.* permissions, so a *positive*
    # resource condition (only allow if the resource matches a corpus bucket) would also
    # gate the discoveryengine calls, since their resource names never look like a GCS
    # bucket path.
    #
    # The state-bucket half of this is closed: every binding of this role carries an
    # *exclude* condition naming the state bucket specifically (see the locals block in
    # bindings.tf and the mirrored logic in deployment/mise.toml's grant task), which is
    # safe on a mixed role because it evaluates true -- permission granted -- for
    # anything that is not literally that one bucket, including every discoveryengine
    # call. What remains open is a *promoted production* corpus bucket: no such bucket
    # has a name committed anywhere in this repository yet, so there is nothing yet to
    # name in an exclude condition for it. Revisit once the environment-pointer files
    # land and a promoted bucket's name becomes a value this module can read.
    "storage.objects.get",
    "storage.objects.list",
    # storage.objects.delete is deliberately absent, and its absence does more than
    # withhold deletion. GCS evaluates a delete check alongside every objects.create
    # as the would-be-overwrite case -- observed denied 14 times, once per object, in
    # an upload that nonetheless succeeded because none of them existed yet. So
    # omitting it makes an upload into an artifact that already has objects fail
    # rather than silently replace them, which is the "create fresh, never mutate"
    # convention enforced by the role instead of only by upload_to_gcs refusing an
    # existing bucket.
    "discoveryengine.dataStores.create",
    "discoveryengine.documents.import",
    "discoveryengine.engines.create",
    "discoveryengine.engines.list",
    # Enumerate datastores, which this role needs and tfaContributor does not. It
    # is what lets `list-artifacts` close its last gap: the listing is built from
    # buckets, so a datastore whose bucket was deleted by hand belongs to no
    # artifact and the reaper can never reach it. Comparing the two enumerations is
    # the only thing in the project that surfaces those orphans.
    "discoveryengine.dataStores.list",
    # Every create and import above returns a long-running operation, and the
    # scripts block on it. Polling is a separate authorization check against the
    # operation resource, so without this the role can start work it cannot watch:
    # observed 93 times in a single create-datastore/create-app run.
    "discoveryengine.operations.get",
    # Record the artifact's manifest, and clear its TTL lease on promotion. Promotion
    # is meant to be the one mutation this role has, and the intent is that it only
    # ever makes things live longer -- but the permission is project-wide and GCS
    # bucket updates are not limited to labels. storage.buckets.update is also what
    # lets a bucket's lifecycle rules, soft-delete policy, versioning and retention be
    # changed, so it can be used to add an immediate-delete lifecycle rule to any
    # bucket in the project, including a promoted production corpus or the OpenTofu
    # state bucket -- functionally equivalent to the delete this role deliberately
    # withholds. Same shape as storage.objects.get above, and the same fix: the state
    # bucket is excluded at the binding, the production-corpus case stays open pending a
    # committed bucket name to exclude.
    "storage.buckets.update",
  ]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_custom_role" "reaper" {
  role_id     = "tfaReaper"
  title       = "Tenant First Aid scratch-artifact reaper"
  description = "Collect expired, unreferenced corpus artifacts. Held by a service account, never a person, and complete on its own rather than layered."
  stage       = "GA"

  # Same root cause as tfaCorpusMaintainer's above: storage.buckets.delete and
  # storage.objects.delete are project-wide, so nothing here stops the reaper's own
  # service account from being used (by a bug or a compromised trigger) to delete an
  # unrelated bucket, not only an expired scratch artifact. The reference veto that makes
  # the reaper safe lives entirely in its reviewed code, not in IAM -- see README.md's
  # "The roles, and where the line is drawn". The OpenTofu state bucket specifically is
  # excluded at the binding (bindings.tf's locals block); a promoted production corpus
  # bucket is not, for the same "no committed name to exclude yet" reason noted above.
  permissions = [
    # Find candidates and read their leases and manifests.
    "storage.buckets.list",
    "storage.buckets.get",
    "storage.objects.list",
    "storage.objects.get",
    # Unmark each datastore from the bucket's manifest as it is collected.
    "storage.buckets.update",
    "storage.objects.create",
    # Collect, in dependency order: apps, then datastores, then the bucket.
    "discoveryengine.engines.list",
    "discoveryengine.engines.delete",
    "discoveryengine.dataStores.delete",
    "storage.objects.delete",
    "storage.buckets.delete",
    # Deleting a datastore returns a long-running operation that Datastore.delete
    # blocks on, so collecting one needs the poll as well as the delete. Deleting an
    # app does not -- delete_engine is fire-and-forget -- but the datastore half is
    # enough to require this.
    "discoveryengine.operations.get",
  ]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_project_iam_custom_role" "corpus_admin" {
  role_id = "tfaCorpusAdmin"
  title   = "Tenant First Aid corpus admin (break glass)"
  # A custom role description is capped at 300 characters by the IAM API, which rejects
  # a longer one at apply time rather than truncating. The fuller reasoning is in
  # README.md; this stays within the cap.
  description = join(" ", [
    "Adds to tfaContributor deletion of corpus artifacts the reaper will not collect:",
    "unleased, promoted, corrupt or orphaned. Granted for a task, then removed. Riskier",
    "than the reaper's own role: the reference veto that protects production lives in the",
    "reaper's code and is only advisory here.",
  ])
  stage = "GA"

  # Same root cause and same fix as tfaCorpusMaintainer's and tfaReaper's above: these
  # storage permissions are project-wide, so every binding of this role (bindings.tf and
  # deployment/mise.toml's grant task) excludes the OpenTofu state bucket specifically. A
  # promoted production corpus bucket is not excluded, for lack of a committed name to
  # exclude -- the one gap this role cannot close any better than the other two can.
  permissions = [
    # Layered on tfaContributor. What it adds is the reaper's collection powers in
    # human hands...
    "storage.buckets.get",
    "storage.buckets.update",
    "storage.objects.list",
    "storage.objects.get",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.buckets.delete",
    "discoveryengine.engines.list",
    "discoveryengine.engines.delete",
    "discoveryengine.dataStores.delete",
    "discoveryengine.operations.get",
    # ...plus undoing a deletion, which the reaper never needs and a human does.
    # The bucket is the only recoverable part of an artifact; datastores and apps
    # have no soft delete at all.
    "storage.buckets.restore",
    "storage.objects.restore",
  ]

  lifecycle {
    prevent_destroy = true
  }
}
