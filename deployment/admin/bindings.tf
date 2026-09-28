# google_project_iam_member, never _binding or _policy.
#
# All three exist and look interchangeable. google_project_iam_policy is authoritative
# for the whole project and would delete every binding not in this file;
# google_project_iam_binding is authoritative for one role and silently evicts other
# members of it. This project's IAM was set up by hand and is not under IaC, so either
# would destroy access on the first apply. _member is additive: it adds one principal
# to one role and leaves everything else alone.

# Must match the bucket in versions.tf's backend block and state_bucket in
# deployment/mise.toml. Three copies rather than one shared source, because Tofu cannot
# read its own backend config as a value and the mise tasks are a separate toolchain --
# the name is not a credential (IAM governs access), so the risk is drift, not exposure.
#
# The three roles below mix storage.* with discoveryengine.* permissions, and roles.tf
# documents that a *positive* resource condition -- "only allow if the resource matches
# this bucket" -- would be unsafe on a mixed role: a discoveryengine call's resource name
# never looks like a GCS bucket path, so it would evaluate false and the condition would
# silently strip every discoveryengine permission the role carries. This is the opposite
# shape: *exclude* one specific, known bucket rather than *allow* a class of them. It
# evaluates true (permission granted) for anything that is not literally this bucket --
# including every discoveryengine call, whose resource name can never equal or be
# prefixed by a GCS bucket path in the first place -- so it narrows storage access
# without touching discoveryengine calls at all, and without inventing a corpus bucket
# naming convention this project does not otherwise have.
#
# It does not close the parallel gap for a *promoted production* corpus bucket, because
# no such bucket has a name committed anywhere in this repository yet -- it is chosen by
# an operator's --bucket argument to upload-to-gcs. Excluding it here would mean guessing
# a name, which is worse than the gap it would claim to close. Revisit once the
# environment-pointer files land (see the plan) and a promoted bucket's name is a value
# this module can read.
#
# Unverified: whether GCP accepts a condition at all on a binding whose role carries
# discoveryengine.* permissions. If it does not, `tofu apply` or `mise run
# //deployment:grant` fails loudly on the first attempt naming the unsupported
# permission -- a safe failure, not a silent one -- rather than the condition being
# quietly ignored.
locals {
  state_bucket = "tenantfirstaid-tofu-state"
  exclude_state_bucket_condition = {
    title       = "tfa exclude state bucket"
    description = "Withholds this role's storage permissions from the OpenTofu state bucket. Its discoveryengine permissions are unaffected: their resource names never match a GCS bucket path."
    expression  = "resource.name != \"projects/_/buckets/${local.state_bucket}\" && !resource.name.startsWith(\"projects/_/buckets/${local.state_bucket}/\")"
  }
}

# The two human personas are bound only if a group was supplied. By default they are
# not, and the project admin assigns the custom roles by hand as they always have -- see
# variables.tf for why that is the default and why it is safe. A count guard rather than
# a shape change: the plan reserves its objection to conditionals for environments that
# differ in architecture, not for a feature that is genuinely optional.
resource "google_project_iam_member" "contributor" {
  count = var.contributor_group == null ? 0 : 1

  project = var.project_id
  role    = google_project_iam_custom_role.contributor.id
  member  = var.contributor_group
}

resource "google_project_iam_member" "corpus_maintainer" {
  count = var.corpus_maintainer_group == null ? 0 : 1

  project = var.project_id
  role    = google_project_iam_custom_role.corpus_maintainer.id
  member  = var.corpus_maintainer_group

  condition {
    title       = local.exclude_state_bucket_condition.title
    description = local.exclude_state_bucket_condition.description
    expression  = local.exclude_state_bucket_condition.expression
  }
}

resource "google_project_iam_member" "reaper" {
  project = var.project_id
  role    = google_project_iam_custom_role.reaper.id
  member  = "serviceAccount:${google_service_account.reaper.email}"

  condition {
    title       = local.exclude_state_bucket_condition.title
    description = local.exclude_state_bucket_condition.description
    expression  = local.exclude_state_bucket_condition.expression
  }
}

# Empty by default, like the two above. If it is set, it is a list rather than a group
# because this is the only role that can destroy a corpus a deployed environment is
# serving, so widening it should take a deliberate act per person rather than a
# membership change someone else can make. Not because the list is reviewable -- it is
# not; terraform.tfvars is gitignored and must stay so, since this repository is public.
resource "google_project_iam_member" "corpus_admin" {
  for_each = toset(var.corpus_admin_members)

  project = var.project_id
  role    = google_project_iam_custom_role.corpus_admin.id
  member  = each.value

  condition {
    title       = local.exclude_state_bucket_condition.title
    description = local.exclude_state_bucket_condition.description
    expression  = local.exclude_state_bucket_condition.expression
  }
}

# ---------------------------------------------------------------------------
# This is what the reaper needs in order to be *invoked*, as opposed to what it does.
# ---------------------------------------------------------------------------
#
# The custom role above covers the deletes. These two are about the plumbing that gets
# the function running at all: a Cloud Functions v2 function triggered by Pub/Sub is a
# Cloud Run service behind an Eventarc trigger, and the trigger's identity -- which is
# the reaper's own service account, by design, rather than the default compute account
# that holds Editor on most projects -- must be able to receive the event and invoke the
# service.
#
# Predefined roles here rather than custom ones: these are platform wiring, not a
# persona, and neither grants anything over corpus artifacts. They live in admin/ because
# they are still IAM, and keeping every setIamPolicy call in one rarely-applied module is
# the property that lets deployment/reaper/ be applied by a maintainer.

resource "google_project_iam_member" "reaper_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.reaper.email}"
}

resource "google_project_iam_member" "reaper_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.reaper.email}"
}
