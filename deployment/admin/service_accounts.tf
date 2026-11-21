# The reaper runs as its own identity rather than as anyone's user account. That is
# what makes "the only thing that can delete a live corpus is code in this repository"
# true: the service account holds delete permissions, and the only thing holding the
# service account is the scheduled function.

resource "google_service_account" "reaper" {
  account_id   = "tfa-corpus-reaper"
  display_name = "Tenant First Aid corpus reaper"
  description  = "Collects expired, unreferenced corpus artifacts. Planned collection code, not yet in this repository; see tfaReaper in roles.tf for what it will hold."
}

# TODO: this is not the project's only service account, and the other two hand-created
# ones should move into this module too, once each is understood well enough to import
# safely. As of 2026-09-29, the IAM console lists two more besides this one:
#
#   - tenantfirstaid@tenantfirstaid.iam.gserviceaccount.com -- the likely identity behind
#     the GOOGLE_SERVICE_ACCOUNT_CREDENTIALS secret used by pr-check.yml,
#     deploy.production.yml and deploy.staging.yml, but unconfirmed: whoever holds that
#     secret should check its client_email against this account before relying on the
#     guess. Its actual consumers need tracing before `terraform import`, since importing
#     without understanding what depends on it risks a plan that wants to change roles a
#     live consumer needs.
#   - langsmith-deployment@tenantfirstaid.iam.gserviceaccount.com -- ruled out as the CI
#     account above. Its own description already says what it is for: "for use in CodePDX
#     Plus/TenantFirstAid (LangSmith Org/Workspace) deployment" -- LangSmith's own hosted
#     deployment product, not this repo's CI/CD.
#
# The default Compute Engine service account is not an import candidate, since GCP owns
# its lifecycle.
