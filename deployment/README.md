# Deployment

Everything describing **how this application is deployed and what it runs against**.
The narrative — CI/CD, secrets, droplet setup, troubleshooting — is in
[Deployment.md](../Deployment.md); this directory holds the files themselves.

Note that "deployment" here is distinct from the **Infrastructure** checkbox in the PR
template, which this project uses for CI, automation and dependency maintenance. Changes
under this directory affect what runs in production and staging.

## Contents

| Path | Holds | Applied by |
|------|-------|------------|
| [`admin/`](admin/README.md) | Service account, the four custom roles, and their bindings — see its README for why capability is code and roster is not | `mise run //deployment:apply-admin`, by an Owner or `projectIamAdmin` holder — see [Bootstrap](#2-the-iam-configuration) |

`admin/` also holds [`billing-quota.md`](admin/billing-quota.md), a placeholder note on why
there is no project spend cap, what the provider offers instead, and which quota dimensions
actually exist. Nothing in it is implemented.

## Permissions the corpus tooling needs

Derived from the API calls the scripts actually make, not guessed. They are listed
per tool rather than as one union, so each can be granted its own minimum — the
reaper is the only one that needs to delete anything. The custom roles in
[`admin/roles.tf`](admin/roles.tf) are built from this table. The artifact-lifecycle
commands (`list-artifacts` through `undelete-bucket`) arrive with the ephemeral
corpus-generation tooling; their rows are here so the roles are defined once, up front.

| Tool | Permissions |
|------|-------------|
| `mise run list-artifacts` | `storage.buckets.list` alone for the inventory; `storage.objects.get` adds each artifact's datastores, and `discoveryengine.dataStores.list` adds the ones belonging to no artifact. It degrades rather than failing, so the first is the only requirement. |
| `mise run promote-artifact` | `storage.buckets.get`, `storage.buckets.update` |
| `mise run upload-to-gcs` | `storage.buckets.create`, `storage.objects.create` |
| `mise run create-datastore-gcs` | `discoveryengine.dataStores.create`, `discoveryengine.documents.import`, `storage.buckets.get`, `storage.objects.create` |
| `mise run create-app-gcs` | `discoveryengine.dataStores.get`, `discoveryengine.engines.create` |
| `mise run reap-artifacts` | all of the above reads, plus `storage.buckets.delete`, `storage.objects.delete`, `discoveryengine.dataStores.delete`, `discoveryengine.engines.list`, `discoveryengine.engines.delete` |
| `mise run delete-artifact` | everything `reap-artifacts` needs. It exists for what the reaper cannot reach, not for anything it cannot do. |
| `mise run undelete-bucket` | `storage.buckets.list`, `storage.buckets.restore`, `storage.objects.restore` |

Each command prints its own list when it hits a `403`, so a contributor learns what
is missing without reading this file first.

**Why this is documented in a public repo.** IAM permission *names* are public GCP
API surface; knowing that a tool calls `storage.buckets.list` gives an attacker
nothing, since without credentials it is useless and with credentials it is
discoverable anyway. The real hazard runs the other way: an undocumented
permission set is how a maintainer ends up granting `roles/owner` to make
something work. Publishing the minimum is what makes least privilege achievable.

What is deliberately *not* here: service-account emails, key material, and project
numbers.

When the reaper is deployed, these become its service account's role. Granting it
the delete permissions and nothing else is the reason the list is split by tool.


## Bootstrap: the parts a human does once

Three things cannot be created by the configuration that depends on them. Each is done
once, by hand, and is documented here as setup rather than pretended to be managed.

### 1. The remote state bucket

The GCS bucket holding OpenTofu's state cannot be created by the configuration whose state
lives in it. The standard chicken-and-egg exception, so it is made once by hand:

    gcloud storage buckets create gs://tenantfirstaid-tofu-state \
      --project=tenantfirstaid --location=US \
      --uniform-bucket-level-access --public-access-prevention \
      --soft-delete-duration=31d

    gcloud storage buckets update gs://tenantfirstaid-tofu-state --versioning

Versioning is the part that matters: it is what makes a corrupted or truncated state file
recoverable, and state is the one thing here with no other backup. Soft delete covers the
other direction — someone deleting the bucket itself. The platform default is 7 days;
GCS permits 7 to 90, and 31 is cheap insurance for the one file with no other backup.

The name is committed, in each root module's `backend` block, rather than passed at init.
A bucket name is not a credential — IAM governs access, and `tofu` prints the name in init
output and lock messages regardless — whereas a partial backend configuration means a typo
does not fail but silently initialises *empty* state, after which the plan proposes
creating every custom role from scratch against `prevent_destroy`. One `tofu init` with no
flags is both safer and simpler.

### 2. The IAM configuration

`deployment/admin/` defines the service account, the four custom roles and the reaper's
bindings. Applying it needs project-level `resourcemanager.projects.setIamPolicy`, plus
`iam.roles.create` and `iam.serviceAccounts.create` — privileges a maintainer does not have
and should not need for routine work.

**Who can apply it: a project Owner.** No single other predefined role is sufficient,
which is easy to get wrong — the three permissions live in three different roles, and none
of those roles contains the other two:

| | `iam.roles.create` | `iam.serviceAccounts.create` | `projects.setIamPolicy` |
|---|---|---|---|
| `roles/resourcemanager.projectIamAdmin` | no | no | **yes** |
| `roles/resourcemanager.organizationAdmin` (org-level, inherits down) | no | no | **yes** |
| `roles/iam.roleAdmin` | **yes** | no | no |
| `roles/iam.serviceAccountAdmin` | no | **yes** | no |

So an apply by a `projectIamAdmin` holder fails on the first `google_project_iam_custom_role`,
having created nothing. The alternative to Owner is holding all three of `iam.roleAdmin`,
`iam.serviceAccountAdmin` and `projectIamAdmin` (or `organizationAdmin`) together.

**A `projectIamAdmin` holder can nonetheless apply it, by granting themselves the roles
they are missing for the length of the apply:**

    mise run //deployment:apply-admin --elevate

That is not a loophole being exploited. `setIamPolicy` is the permission that grants
permissions, so anyone holding it can already give themselves anything at any moment; the
task adds no capability. What it adds is that the escalation is explicit, bounded and
legible rather than a console click that stays granted:

* **Time-boxed.** Each binding carries a `request.time` condition, so it lapses on its own
  even if the revoke never runs — a closed laptop or a Ctrl-C mid-apply cannot leave a
  standing `roleAdmin` grant behind.
* **Narrow.** Only `iam.roleAdmin`, `iam.serviceAccountAdmin` and `storage.admin`, only for
  roles the caller does not already hold, and never Owner. The third is there because
  `tofu init` reads the state bucket and `storage.buckets.get` is in none of the other two
  — nor in any of the four roles this project defines. It is also the one grant broad
  enough to matter if it outlived its window, so it is narrowed by *resource* as well as by
  time: its condition pins it to `projects/_/buckets/tenantfirstaid-tofu-state` and the
  objects under it, so it cannot touch a corpus bucket even while live. The two narrower
  storage roles do not work here — `roles/storage.editor` carries neither `buckets.get` nor
  `buckets.update`, and `roles/storage.legacyBucketOwner` cannot be bound at project level
  at all.
* **Logged.** `SetIamPolicy` is an Admin Activity write, which is always on and cannot be
  disabled, so the grant and the revoke are both permanently in the audit log.

Elevation is opt-in, never the default. An Owner already holds everything and should run
the task without `--elevate`; someone who is neither will get a plain 403 naming the
permission they lack, which is the right thing to read before deciding to escalate. A task
that silently reached for `setIamPolicy` on behalf of anyone who ran an apply would be the
opposite of the property this is for. `--plan-only` stops after the plan, and a caller who
holds nothing will need `--elevate` alongside it, since the plan refreshes state.

Ask in the Discord channel
[#tenantfirstaid-general](https://discord.com/channels/1068260532806766733/1367177752792531115),
the same route the README already uses for access requests.

*(Verified against the live IAM API by reading each predefined role's `includedPermissions`,
not from documentation. Every permission claim in this file is derived that way, or by
running the thing and reading the 403 — the roles here are not what their names suggest,
and `projectIamAdmin` in particular sounds sufficient for this module and is not.)*

> Deliberately no names or email addresses here. This repository is public. Permission
> *names* are public GCP API surface and safe to publish — which is why the table above
> exists — but the identities holding them are personal addresses. Name the role and the
> channel; let `gcloud projects get-iam-policy` answer who, to whoever is entitled to ask.

Everything else — `reaper/`, and later `envs/<name>/` — is applied by a maintainer, taking
the reaper's service-account email as an input rather than creating it. That split is a
security property, not a convenience: if routine applies never need `setIamPolicy`, then a
compromised laptop or a bad plan cannot escalate privileges — the worst it can do is break
the environment it already governs.

### 3. Nothing. Role assignment stays manual, on purpose

There is no third bootstrap step. `deployment/admin/` applies from `project_id` alone,
creating the four custom roles, the reaper's service account and the reaper's bindings —
eight resources, none of them naming a person.

**Human roles are assigned by hand by the project admin, exactly as they always have
been.** The only change is which role gets named: a custom one from `roles.tf` instead of
a broad predefined one. Ask in the Discord channel, as before. Once `admin/` is applied:

    # the contributor, after signing in, sends the admin this exact line:
    mise run //backend:whoami                             # -> user:someone@gmail.com

    # the admin pastes it verbatim:
    mise run //deployment:grant user:someone@gmail.com                     # tfaContributor
    mise run //deployment:grant user:someone@gmail.com --role corpus-maintainer
    mise run //deployment:grant user:someone@gmail.com --expires 90        # lapses on its own
    mise run //deployment:grant user:someone@gmail.com --revoke            # offboarding
    mise run //deployment:list-access                                      # who holds what

The roles are layers, so the maintainer line above grants `tfaContributor` alongside
`tfaCorpusMaintainer`. `tfaCorpusAdmin` is the one meant to be handed back, so grant it for
a task and let it lapse; the base layer underneath stays, and a revoke removes only the
layer named:

    mise run //deployment:grant user:someone@gmail.com --role corpus-admin --expires 1
    mise run //deployment:grant user:someone@gmail.com --role corpus-admin --revoke

The contributor reports their own identity rather than the admin being told an address:
it proves control of the credential GCP will authenticate, and removes the chance to
mistype an address rather than merely detecting it afterwards.

No personal address is ever an input to the OpenTofu configuration, and
`terraform.tfvars` is gitignored and must stay so: this repository is public.

**Why the roster is not managed by OpenTofu**, why `google_project_iam_member` is the only
safe resource here, why applying this module is admin-equivalent while applying `reaper/`
is not, and why Google Groups remain the intended end state — all in
[`admin/README.md`](admin/README.md), which is the place that architecture is written down.

### Checking the bootstrap is done

    mise run //deployment:check                    # formatting and config validity

It needs no GCP credentials. The first apply of `deployment/admin/` is what proves the
rest, and it fails loudly if a permission name is wrong — which is the real verification
for the permission table above.
