# `deployment/admin/`

The IAM configuration: four custom roles, the reaper's service account, and the bindings
that are safe to keep in code. Applied rarely, by a project admin, and separately from
everything else in `deployment/`.

This file explains *why* it is separate, because the separation is load-bearing in three
different directions and none of them is obvious from the `.tf` files alone.

---

## The three separations

| | Lives in git, under Tofu | Lives outside, out of band |
|---|---|---|
| **Capability** | what a role *can do* — `roles.tf` | — |
| **Roster** | — | who *holds* a role — the project IAM policy |
| **Privilege to apply** | this module, needing `setIamPolicy` | `reaper/`, `envs/` — needing none |

Each row is a deliberate cut. Read on for why each one is where it is.

---

## 1. Capability is code. Roster is not.

**The roles are the durable, reviewable artifact. Who holds them is not.**

Before this module existed, access was granted by hand and the role was unnamed, so
nobody could answer "what can a contributor do?" — and the answer turned out to be wrong
in both directions: a maintainer could not run `list-artifacts` (`storage.buckets.list`
denied) while a contributor who only needed to query a datastore may have held far more.

`roles.tf` fixes that half. Every permission in it was derived by running the tooling and
reading the 403, not guessed, and the comments record which run demanded which permission.
That is what makes the maintainer/reaper split real rather than aspirational:
`tfaCorpusMaintainer` genuinely cannot delete a corpus, because the permission is absent
from the role rather than merely absent from the documentation.

The roster half stays out of the repository, and that is not a compromise — it is the
better design for three independent reasons.

### It cannot go in git, because of PII

This repository is public. A contributor's Google account is a personal email address.
`terraform.tfvars` is gitignored and must stay so, which means anything Tofu needs to know
about a person can only reach it through a file that is never committed.

It is tempting to argue that the most dangerous role's membership at least belongs in a
reviewable diff. It cannot: the only file that could carry it is never committed, so the
reviewability would be imaginary while the addresses would be real, sitting one
`git add -f` from publication. Review the *roles* in git; audit the *roster* in the IAM
policy and the Admin Activity log.

### It should not go in Tofu, because Tofu converges

`google_project_iam_member` is convergent: a principal Tofu binds must be present in the
configuration at *every* apply, or the next apply removes them.

So a Tofu-managed roster has to live somewhere Tofu reads. Git is out, per the above,
which leaves a laptop-local gitignored tfvars — and then a second admin's apply silently
de-provisions everyone the first admin added. That is precisely the "concurrency breaks"
failure this project already documented for corpus generations, reappearing in IAM, where
the cost is people losing access rather than a rebuildable artifact being lost.

### The place it does live is better audited than a file

`SetIamPolicy` is an Admin Activity write. Admin Activity logging is always on, free, and
cannot be disabled. Every grant and every revoke is therefore permanently recorded with
who performed it and when — a stronger record than a tfvars file on someone's laptop, and
the same record whether the grant came from this repository's tooling or from a click in
the console.

### How the roster is actually managed

Onboarding is two commands run by two different people, and the order matters:

    # the contributor, once they have signed in with `mise run //:gcloud-login`
    mise run //backend:whoami          ->  user:someone@gmail.com

    # a project admin, pasting that line verbatim
    mise run //deployment:grant user:someone@gmail.com
    mise run //deployment:grant user:someone@gmail.com --role corpus-maintainer
    mise run //deployment:grant user:someone@gmail.com --expires 90
    mise run //deployment:grant user:someone@gmail.com --revoke
    mise run //deployment:list-access

**Why the contributor reports their own identity, rather than the admin being told an
address.** This is the part of onboarding that would otherwise want an invite system --
mail a secret to the address, have the person send it back -- and the handoff above is
stronger than one on both counts that motivates the idea.

*Control of the account.* An emailed secret proves someone can read mail at an address.
Mail is forwarded, aliased, and shared. `whoami` prints the `email` claim from a token
Google has just issued, so it proves they hold working credentials for the account GCP
will actually authenticate.

*Typos.* The handoff does not detect a mistyped address, it removes the opportunity to
make one: nobody types the address, it is machine-generated and pasted. And an invite
flow would make that failure mode worse rather than better. Today a typo **fails closed**
-- `someone@gmial.com` binds, matches nobody, grants nothing, and is inert. Mailing a
redeemable secret to a mistyped-but-real address **fails open**. Gmail also ignores dots
and honours `+tags`, so a whole class of address typos would be delivered anyway and the
check would pass having established nothing.

The general principle: we do not own the identity system here, Google does, so
verification is delegated to it rather than reimplemented beside it.

### Expiring grants

`--expires <days>` attaches a `request.time` condition, so the binding lapses on its own
and a contributor who still needs access re-asks. Minimising *standing* privilege is the
part of modern access practice worth adopting here, and unlike address typos it has no
other mitigation.

It is opt-in rather than the default, because a grant that silently expires mid-task is
its own failure mode, and the right default depends on how the project actually onboards.
`--revoke` passes `--all`, so it removes a binding whether or not it carries a condition;
a revoke that named no condition would report success while leaving an expiring grant in
place.
`grant` wraps `gcloud projects add-iam-policy-binding` with the role names from this
module, validates the principal, refuses if the role does not exist yet (pointing at
`apply-admin` instead of reporting a confusing typo), and requires a typed confirmation
for `corpus-admin`. It needs `resourcemanager.projects.setIamPolicy`, which a
`projectIamAdmin` holder or Owner already has — no elevation.

**It binds a role to an identity that already exists; it never creates one.** There is no
such thing as creating a user in GCP — a Google account is made by the person at
accounts.google.com and merely *referenced* by an IAM policy. The same is true of a group,
which must already exist at groups.google.com. The only identity anything here creates is
the reaper's service account, in `service_accounts.tf`.

That has a failure mode worth knowing: **a typo binds nobody and reports success.** GCP
does not verify that an address corresponds to a real account, and the task validates only
its syntax. The result is a binding in the policy that never matches anyone, a contributor
still getting 403s, and an admin looking at a grant in the console that appears correct.

Nothing on the granting side can close that gap. The only proof is the person signing in,
which is why the task ends by asking for it:

    gcloud auth application-default login
    mise run //backend:gcloud-login-check

Until that passes, treat the grant as unverified.

---

## 2. Additive bindings, or hand assignment and IaC cannot coexist

`bindings.tf` uses `google_project_iam_member` — never `_binding`, never `_policy`.

All three resources exist and look interchangeable:

| Resource | Authoritative over | Effect on a hand-made grant |
|---|---|---|
| `google_project_iam_policy` | the entire project policy | **deletes every binding not in this file** |
| `google_project_iam_binding` | one role | **evicts every other member of that role** |
| `google_project_iam_member` | one (role, member) pair | leaves everything else alone |

This project's IAM was set up by hand and has never been under IaC, so either of the first
two would destroy access on the first apply. `_member` is the only safe choice.

That is not merely a migration concern that expires once things settle. **It is what makes
section 1 possible at all.** A grant made in the console is not in Tofu state, so an apply
neither knows nor cares about it. Hand assignment and IaC coexist by construction —
capability managed as code, roster managed live, neither fighting the other.

---

## 3. Applying this module is admin-equivalent, so nothing else may need it

Applying `admin/` needs `iam.roles.create`, `iam.serviceAccounts.create` and
`resourcemanager.projects.setIamPolicy` together. The third is the significant one:
**anyone who can set the project IAM policy can grant themselves anything**, so "may apply
the IAM config" is admin-equivalent in blast radius even though none of the three roles is
literally Owner.

Verified against the IAM API rather than the documentation:

| Role | `iam.roles.create` | `iam.serviceAccounts.create` | `projects.setIamPolicy` |
|---|---|---|---|
| `roles/resourcemanager.projectIamAdmin` | no | no | **yes** |
| `roles/resourcemanager.organizationAdmin` | no | no | **yes** |
| `roles/iam.roleAdmin` | **yes** | no | no |
| `roles/iam.serviceAccountAdmin` | no | **yes** | no |

No single predefined role short of Owner holds all three, so a `projectIamAdmin` holder
fails on the first `google_project_iam_custom_role` having created nothing.
`mise run //deployment:apply-admin --elevate` closes that gap by granting the missing
roles for the length of the apply and dropping them afterwards — see the root
[README](../README.md) for what that does and why it is not a loophole.

**The consequence for everything else in `deployment/` is the point of this separation.**
Because every `setIamPolicy` call in the project lives in this one rarely-applied module,
applying `reaper/` and later `envs/<name>/` needs no privilege *this* module grants: they
take the reaper's service-account email as an input rather than creating it. So a
compromised maintainer laptop, or a bad plan in an operational module, cannot escalate
privileges — the worst it can do is break the environment it already governs. That is
narrower than "needs no privileges at all": a maintainer applying `reaper/` still needs
whatever Cloud Functions, Eventarc, Pub/Sub and Cloud Scheduler deploy-time permissions
that module requires, none of which are modeled as a role here yet, because nobody has
run that apply and read the 403s.

That is why the reaper's Eventarc and Cloud Run bindings are *here* rather than next to
the function they serve. They are platform wiring rather than a persona, and they would be
more natural in `reaper/` — but putting them there would mean a maintainer applying the
reaper needs `setIamPolicy`, which would forfeit the property above for the sake of tidier
file placement.

---

## The roles, and where the line is drawn

| Role | For | Adds |
|---|---|---|
| `tfaContributor` | anyone running the app or an evaluation locally | query datastores and call the model — read only |
| `tfaCorpusMaintainer` | whoever provisions scratch artifacts | create buckets/datastores/apps, upload, promote |
| `tfaCorpusAdmin` | granted for a task, then removed | delete by hand, including promoted artifacts; restore a soft-deleted bucket |
| `tfaReaper` | the reaper's service account, no humans | *(not layered)* delete buckets, datastores and apps |

**The three human roles are layers, not bundles.** `tfaContributor` is the base every
person holds; the other two carry only what they add on top of it. A maintainer holds two
roles, and reads the corpus through the contributor one. IAM allow policies are additive,
so the effective set is the union, and `mise run //deployment:grant` binds the whole stack
in one command — `--role corpus-maintainer` grants both.

The layering is there for `tfaCorpusAdmin`, which is meant to be held briefly and handed
back. Peeling off one layer returns someone to ordinary access; revoking a self-contained
superset would strip their day-to-day permissions with it, and a revoke that breaks
somebody's laptop is a revoke that gets postponed. So `--revoke` removes only the layer
named, and `--expires` time-bounds only that layer, leaving the base permanent. That also
means a bare `--role contributor --revoke` is not full offboarding on its own for someone
who was also granted a higher layer — it leaves that layer bound. Fully offboarding them
takes one revoke per layer they hold, highest first (see the root
[README](../README.md#3-nothing-role-assignment-stays-manual-on-purpose)).

`tfaReaper` is the exception and is complete on its own. It belongs to a service account
holding nothing else, and it must not inherit permissions shaped for people.

**The split is drawn at destruction, not at convenience.** A corpus maintainer can create
anything and promote artifacts but cannot delete directly — no role here grants
`storage.objects.delete` or `storage.buckets.delete` to a human. So the only identity that
can routinely remove a live corpus is a scheduled job whose behaviour is in this repository
and gated by the reference veto. That is worth more than the convenience of a single role.

**That line is narrower than it sounds.** `tfaCorpusMaintainer`, `tfaReaper` and
`tfaCorpusAdmin` all hold `storage.buckets.update` at project scope, which can add a
bucket lifecycle rule that deletes its objects immediately — functionally equivalent to
the delete permission each role deliberately withholds, and not limited to the corpus
buckets any of them is meant to touch (`tfaCorpusMaintainer`'s `storage.objects.get` has
the same project-wide reach, and would read OpenTofu state). A *positive* resource
condition can't close this: these roles mix `storage.*` with `discoveryengine.*`
permissions, and scoping the binding to "corpus buckets only" would need a bucket-naming
convention this project does not have, and would in any case gate the `discoveryengine.*`
calls too, since their resource names never look like a GCS bucket path.

The OpenTofu state bucket is closed anyway, by inverting the shape: every binding of these
three roles carries a condition that *excludes* that one named bucket rather than
*allowing* a class of them (see the `locals` block in `bindings.tf`, mirrored in
`deployment/mise.toml`'s `grant` task). An exclude condition evaluates true — permission
granted — for anything that is not literally that bucket, including every
`discoveryengine.*` call, so it narrows storage access without the positive form's risk of
silently gating discoveryengine permissions.

That last claim carried a caveat this document previously got wrong. `setIamPolicy`
accepts a condition on a custom role regardless of what permissions it carries — there is
nothing for `grant` or `apply-admin` to reject at apply time. The condition is evaluated
per request instead, and the real open question was whether a `discoveryengine.*` request
populates `resource.name` the way a GCS request does; if it doesn't, `resource.name !=
"..."` could evaluate to true, to false, or to an error, and any of those is a maintainer
hitting a runtime 403 on `create-datastore-gcs` or `documents.import` despite the grant
looking correct — a silent failure, not the loud one this document claimed. The expression
now leads with `resource.service != "storage.googleapis.com" ||`, so every
`discoveryengine.*` permission short-circuits before a `resource.name` comparison is ever
evaluated, and the question is moot rather than merely answered. This has not been checked
against live GCP; before relying on it for a real onboarding, grant `tfaCorpusMaintainer`
to a test principal and run `create-datastore-gcs --dry-run` or `vertex_ai_search` against
it to confirm end to end.

What remains open is a *promoted production* corpus bucket: no such bucket has a name
committed anywhere in this repository yet, so there is nothing yet to name in an exclude
condition for it either. See the matching comments in `roles.tf` for where that stands
per role, and revisit once the environment-pointer files land.

`tfaCorpusAdmin` is consequently **the most dangerous role in the project — more dangerous
than the reaper's.** That inverts the usual assumption and is worth stating plainly: the
reaper cannot delete a referenced artifact, because the veto is in its code and the code is
reviewed. A human with the same permissions has no such constraint. Prefer fixing the
reaper to granting this; most manual deletions are evidence of a gap in its predicate.

`tfaReaper` is deliberately absent from the `grant` task. It belongs to a service account.

---

## Groups: the intended end state, and the narrow reason for it

`contributor_group` and `corpus_maintainer_group` accept a `group:` principal and bind it
when set. They default to `null`, and by default this module binds no humans at all.

The argument for adopting groups is **not** convenience — hand assignment is already one
Discord ask. It is blast radius. Granting a project role requires
`resourcemanager.projects.setIamPolicy`, the permission that grants permissions, so hand
assignment means every onboarding is performed by someone who could escalate to Owner. A
group *owner* needs no GCP permissions whatsoever. Groups decouple "can add a contributor"
from "can take over the project."

A group address is not PII, so setting these variables does not conflict with section 1.
Create the groups at groups.google.com — a Workspace domain is not required, which matters
because contributors use personal accounts — and set **Who can join** to *Only invited
users*, since a joinable group holding `tfaCorpusMaintainer` is a self-service path into
the project.

Adoption is purely additive: create the group, populate it, set the variable, then remove
the hand-made bindings.

**OpenTofu cannot create the groups**, and this has been checked rather than assumed. No
predefined GCP IAM role contains any `cloudidentity.*` permission at all — group
administration is a Workspace admin role granted at `admin.google.com`, in a different
administrative plane that no amount of `setIamPolicy` reaches. Nor can a GitHub team be an
IAM principal for humans: Workforce Identity Federation needs an IdP that issues tokens for
people, and GitHub's OIDC issues them only to Actions workflows.

---

## Files

| File | What it holds |
|---|---|
| `roles.tf` | the four custom roles, with the audit evidence for each permission in comments |
| `bindings.tf` | the reaper's bindings, and the optional group bindings |
| `service_accounts.tf` | the reaper's identity |
| `variables.tf` | inputs, all optional except `project_id` |
| `outputs.tf` | the reaper's email and the role IDs, consumed by other modules |
| `versions.tf` | provider pins and the GCS backend |
| `terraform.tfvars.example` | copy to `terraform.tfvars`, which is gitignored and must stay so |

`prevent_destroy` is set on the roles: a deleted custom role is recoverable for seven days
and its `role_id` is blocked from reuse for thirty, so an accidental destroy is not
something to discover afterwards.
