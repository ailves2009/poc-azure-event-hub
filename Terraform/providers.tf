terraform {
  /*
  backend "local" {
    path = "/home/xxx/keyvault/kv-terraform.tfstate"
  } */
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 2.79.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.5.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {
  use_msi = false
}
