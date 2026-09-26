variable "project_id" {
  description = <<-EOT
    The GCP project these roles and bindings apply to.

    Defaulted rather than required, because there is exactly one and its name is already
    committed in versions.tf's backend and in the mise tasks. Requiring it would mean a
    terraform.tfvars whose only content is a value the repository already states, which
    is a setup step that protects nothing.
  EOT
  type        = string
  default     = "tenantfirstaid"
}

# ---------------------------------------------------------------------------
# Human principals are optional, and by default this module binds none of them
# ---------------------------------------------------------------------------
#
# The roles are the durable, reviewable artifact; who holds them is not. Membership is
# assigned by hand by the project admin, the same way it has always been done here, and
# the only change is that the grant now names a custom role instead of a broad predefined
# one. That is the whole point of the module: "what can a contributor do?" becomes
# answerable from roles.tf, without the repository having to know who the contributors
# are.
#
# This is safe only because bindings.tf uses google_project_iam_member, which is additive
# -- a console-granted binding is not in Tofu state and is never clobbered by an apply.
# With _binding or _policy, hand-assignment and IaC could not coexist at all.
#
# Setting the group variables is the better end state and they are kept for it, because
# granting a project role requires resourcemanager.projects.setIamPolicy -- the permission
# that grants permissions. So hand-assignment means every onboarding is done by someone
# who could escalate to Owner, while a group owner holding no GCP permissions at all can
# add a member. Adopting groups later is purely additive: create the group, add the
# members, set the variable, remove the hand-made bindings.

variable "contributor_group" {
  description = <<-EOT
    Google Group granted read-only access: run the app and evaluations locally.

    Optional. Null means this module binds nobody to the contributor role and the
    project admin assigns it by hand. A group -- never a list of individuals -- so that
    onboarding is a membership change rather than an infrastructure PR, and so that no
    personal address is ever an input to this configuration. Groups created at
    groups.google.com can hold IAM bindings without a Workspace domain, which matters
    because contributors use personal accounts.
  EOT
  type        = string
  default     = null

  validation {
    condition     = var.contributor_group == null || startswith(coalesce(var.contributor_group, "group:"), "group:")
    error_message = "Must be a group principal, e.g. group:tfa-contributors@example.com, or null to assign the role by hand. Individuals are never bound here: this repository is public."
  }
}

variable "corpus_maintainer_group" {
  description = <<-EOT
    Google Group allowed to build corpus artifacts: create and promote, never delete.

    Optional, on the same terms as contributor_group.
  EOT
  type        = string
  default     = null

  validation {
    condition     = var.corpus_maintainer_group == null || startswith(coalesce(var.corpus_maintainer_group, "group:"), "group:")
    error_message = "Must be a group principal, e.g. group:tfa-corpus-maintainers@example.com, or null to assign the role by hand."
  }
}

variable "corpus_admin_members" {
  description = <<-EOT
    Principals allowed to delete corpus artifacts by hand, including promoted ones.

    Optional, and empty by default. Setting it is not the recommended route: prefer a
    grant made with `mise run //deployment:grant --role corpus-admin`, which leaves no
    address on disk at all.

    Membership of this role is not reviewable through git and cannot be made so.
    terraform.tfvars is gitignored and must stay that way, because this repository is
    public and a personal address is PII -- so an address written here buys no
    reviewability while sitting one `git add -f` from publication.

    The audit trail that does exist is the project IAM policy itself, plus the Admin
    Activity log, which records every SetIamPolicy and cannot be disabled. That is a
    better record than a tfvars file, and it is the same one that covers a grant made by
    hand.
  EOT
  type        = list(string)
  default     = []
}
