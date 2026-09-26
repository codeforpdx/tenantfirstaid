# google_project_iam_member, never _binding or _policy.
#
# All three exist and look interchangeable. google_project_iam_policy is authoritative
# for the whole project and would delete every binding not in this file;
# google_project_iam_binding is authoritative for one role and silently evicts other
# members of it. This project's IAM was set up by hand and is not under IaC, so either
# would destroy access on the first apply. _member is additive: it adds one principal
# to one role and leaves everything else alone.

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
}

resource "google_project_iam_member" "reaper" {
  project = var.project_id
  role    = google_project_iam_custom_role.reaper.id
  member  = "serviceAccount:${google_service_account.reaper.email}"
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
