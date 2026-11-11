terraform {
  required_version = ">= 1.9"

  # State is local on purpose: this POC is created and destroyed in one sitting.
  # For a shared environment, use an azurerm backend (Storage Account with
  # Entra ID auth, versioning and a resource lock).

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.13"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }
  }
}

provider "azurerm" {
  features {}

  # Storage keys are disabled on the checkpoint account, so the provider
  # must talk to the data plane with Entra ID as well.
  storage_use_azuread = true

  # subscription_id comes from ARM_SUBSCRIPTION_ID (the Makefile sets it from `az account show`).
}
