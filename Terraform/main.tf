/************************************************************************************************************************************************

  Azure Event Hub Proof of Concept Architecture: Terraform Template

    Create a Event Hub environment based on best practices to achieve a successful proof of concept. While settings can be adjusted, 
    the major deployment differences are based on whether or not you used Private Endpoints for connectivity. If you do not already use 
    Private Endpoints for other Azure deployments, it's discouraged to use them for a proof of concept as they have many other networking 
    depandancies than what can be configured here.

    Resources:

      Resource Group:
          - All of the resources will be created in this Resource Group.
      
      Event Hub Namespace:
          - Container for Event Hubs

      Resource Event Hub:
          - Highly scalable data streaming platform and event ingestion service that can receive and process millions of events per second in real time

      Resource Access Policy
          - Shared Access Policy to access to Event Hub
      Todo:
          - use resource "random_string"
************************************************************************************************************************************************/

terraform {

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

data "azurerm_client_config" "current" {}

// Add a random suffix to ensure global uniqueness among the resources created
//   Terraform: https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/string
resource "random_string" "suffix" {
  length  = 3
  upper   = false
  special = false
}

/************************************************************************************************************************************************
  Resource Group
        All of the resources will be created in this Resource Group.
************************************************************************************************************************************************/
//  Create the Resource Group
//   Azure: https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal
//   Terraform: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group
resource "azurerm_resource_group" "resource-group" {
  name     = "eventhub-rg-poc"
  location = var.azure_region

  tags = {
    ENV     = var.environment
    project = var.project
    created = "terraform"
  }
}

/************************************************************************************************************************************************
  Resource Group Namespace
        All of the Event Hubs will be created in this Namespace.
************************************************************************************************************************************************/
resource "azurerm_eventhub_namespace" "eventhub-namespace" {
  name                = "eventhub-ns-da-poc"
  location            = azurerm_resource_group.resource-group.location
  resource_group_name = azurerm_resource_group.resource-group.name
  sku                 = "Basic"
  capacity            = 2
  tags = {
    ENV     = var.environment
    project = var.project
    created = "terraform"
  }
}

/************************************************************************************************************************************************
  Resource Event Hub
        Highly scalable data streaming platform and event ingestion service that can receive and process millions of events per second in real time
************************************************************************************************************************************************/
resource "azurerm_eventhub" "eventhub-poc1" {
  name                = "eventhub1-poc"
  namespace_name      = azurerm_eventhub_namespace.eventhub-namespace.name
  resource_group_name = azurerm_resource_group.resource-group.name
  partition_count     = 2
  message_retention   = 1
}

/************************************************************************************************************************************************
  Resource Access Policy
        Shared Access Policy to access to Event Hub
************************************************************************************************************************************************/
resource "azurerm_eventhub_authorization_rule" "eventhub_authorization_rule" {
  name                = "eventhub-poc-policy"
  namespace_name      = azurerm_eventhub_namespace.eventhub-namespace.name
  eventhub_name       = azurerm_eventhub.eventhub-poc1.name
  resource_group_name = azurerm_resource_group.resource-group.name
  listen              = true
  send                = true
  manage              = false
}
