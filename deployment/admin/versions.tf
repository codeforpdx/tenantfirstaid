# Applied rarely, and not by a maintainer: this module needs iam.roles.create,
# iam.serviceAccounts.create and resourcemanager.projects.setIamPolicy together, and no
# single predefined role short of Owner holds all three. A projectIamAdmin holder alone
# fails on the first google_project_iam_custom_role, having created nothing -- but can
# still apply it via `mise run //deployment:apply-admin`, which grants the two missing
# roles for the duration and drops them after. See ../README.md, "Bootstrap: the parts a
# human does once".

terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # The bucket is created by hand before any module can run -- the state bucket cannot be
  # created by the configuration whose state lives in it. Its name is committed rather
  # than passed at init: a bucket name is not a credential (IAM governs access, and tofu
  # prints the name in init output and lock messages anyway), while a partial
  # configuration means a typo silently initialises empty state instead of failing, and
  # the plan that follows proposes recreating every role from scratch.
  backend "gcs" {
    bucket = "tenantfirstaid-tofu-state"
    prefix = "admin"
  }
}

provider "google" {
  project = var.project_id
}
