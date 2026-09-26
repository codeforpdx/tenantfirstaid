output "reaper_service_account_email" {
  description = <<-EOT
    The reaper's identity, consumed by deployment/envs/<name>/.

    Passed to the operational modules as an input rather than created there, so that
    applying them never needs setIamPolicy. That split is a security property: if the
    routine path cannot change IAM, a compromised laptop or a bad plan cannot escalate
    privileges, only break the environment it already governs.
  EOT
  value       = google_service_account.reaper.email
}

output "custom_role_ids" {
  description = "The four custom roles, for reference when granting access by hand."
  value = {
    contributor       = google_project_iam_custom_role.contributor.id
    corpus_maintainer = google_project_iam_custom_role.corpus_maintainer.id
    reaper            = google_project_iam_custom_role.reaper.id
    corpus_admin      = google_project_iam_custom_role.corpus_admin.id
  }
}
