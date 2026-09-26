# The reaper runs as its own identity rather than as anyone's user account. That is
# what makes "the only thing that can delete a live corpus is code in this repository"
# true: the service account holds delete permissions, and the only thing holding the
# service account is the scheduled function.

resource "google_service_account" "reaper" {
  account_id   = "tfa-corpus-reaper"
  display_name = "Tenant First Aid corpus reaper"
  description  = "Collects expired, unreferenced corpus artifacts. See backend/scripts/reaper.py."
}
