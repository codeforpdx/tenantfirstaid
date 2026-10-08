# Billing and spend limits

**Status: placeholder. Nothing described here is implemented, and no resource in this
module touches billing or quota.** This file records what was investigated, so the next
person does not repeat it.

## There is no maximum monthly bill

GCP has no "cap this project at $N per month" setting. Not one the provider fails to
expose — one that does not exist. Verified by reading the pinned provider's schema
(`hashicorp/google ~> 6.0`), where `google_billing_budget`'s complete surface is:

    amount           { specified_amount | last_period_amount }
    budget_filter    { projects, services, labels, credit_types, calendar_period }
    threshold_rules  { threshold_percent, spend_basis }
    all_updates_rule { pubsub_topic, monitoring_notification_channels }

There is no enforcement field. A budget is a notification object with a number attached:
it observes spend and can tell you about it, and it cannot stop anything.

Two consequences worth knowing before anyone reaches for it:

- `billing_account` is **required**, so this is a billing-account-scoped resource.
  Applying it needs `billing.budgets.create` on the billing account, which is a different
  surface from the project-level `setIamPolicy` + role-admin rights this module already
  needs. It would be a fourth actor in the bootstrap story, not something the existing
  admin path covers.
- Budget data lags actual spend by hours, so even the alert arrives late.

## The kill switch, and why it is not proposed

Google documents a pattern for turning a budget into a hard stop: `all_updates_rule.pubsub_topic`
→ a Cloud Function calling `projects.updateBillingInfo` to detach the billing account.

It is rejected here for the same reason the reaper fails closed: the failure modes are
wildly asymmetric. Detaching billing stops the **entire project**, production included,
can delete resources rather than pause them, and fires on data that is already hours old.
It is a fire alarm wired to a demolition charge.

## Quota is the enforceable lever, and it is denominated in requests

`google_cloud_quotas_quota_preference` is in the provider and is the only mechanism that
enforces anything synchronously — exceed a limit and the call returns `429
RESOURCE_EXHAUSTED` at request time:

    service, quota_id, dimensions
    quota_config { preferred_value, granted_value [computed] }

Note `granted_value` is **computed**: Google decides whether to honour `preferred_value`.
Lowering a limit is normally auto-approved; raising it goes to review. `ignore_safety_checks`
exists because setting a limit below current usage is a live-fire footgun.

`google_service_usage_consumer_quota_override` is **not** in the 6.x provider, so the
Cloud Quotas resource is the only route.

### What dimensions actually exist

Read from the live API on 2026-09-22, not from documentation:

| Service | Quota limits | Per-principal dimension |
|---|---|---|
| `aiplatform.googleapis.com` | 367 | **none** — 18 distinct unit shapes, all `{project}` ± `{region}` / `{base_model}` |
| `discoveryengine.googleapis.com` | 77 | **one**: `User event collect requests [1/min/{project}/{user}]` |

The single `{user}` limit is on user-event collection — the analytics ingestion endpoint —
not on search, and not on anything the app or a contributor exercises.

**So quota is not a per-persona control.** A quota preference on `tenantfirstaid` throttles
the production droplet, staging, evaluations and contributors indiscriminately, and
production would feel it first. That is the finding that matters: it rules out "give
`tfaContributor` a spending limit" as a shape, because IAM roles are not billing boundaries
and quotas are not principal-scoped.

### The one dimension worth building on

Vertex publishes a **daily** dimension:

    1/d/{project}/{base_model}

A daily request ceiling per base model bounds cost by construction once per-request cost is
known, and it fails gracefully — a 429 on the next call — rather than by detaching billing
from a live project. Paired with `1/min/{project}/{base_model}` it gives two tiers: the
per-minute limit catches a runaway loop within seconds, the daily limit bounds the worst
case. Both are still shared with production, so sizing has to clear legitimate peak load
(production traffic plus a concurrent evaluation run).

That pairing is the concrete thing to build if this work is picked up.

## Blocked on

- **`cloudquotas.googleapis.com` is not enabled.** `serviceusage.googleapis.com` was
  enabled on 2026-09-22; Cloud Quotas was not. It can go through the normal API path now
  that Service Usage is up, under a time-boxed `roles/serviceusage.serviceUsageAdmin` grant
  — see the bootstrap section of [`../README.md`](../README.md).
- Nobody holds `serviceusage.quotas.update`, which `google_cloud_quotas_quota_preference`
  needs.

## The alternative that was deferred

The other shape is to stop sharing a project. Model calls address
`projects/{project}/locations/{loc}/publishers/google/models/...` — Gemini models are
Google-published, not project-hosted — so the project in that path is purely the billing and
quota consumer, and contributors could bill their own sandbox. Search cannot move, because
the datastore is a resource that lives in `tenantfirstaid`.

That split would remove `aiplatform.endpoints.predict` from `tfaContributor` entirely: the
one permission with unbounded cost attached would no longer be granted on the shared
project at all. It needs a code change first — `GOOGLE_CLOUD_PROJECT` currently feeds both
the retriever's `project_id` and the LLM's `project`, so they cannot be pointed at
different projects today.

Deferred by decision, not by difficulty.
