/************************************************************************************************************************************************

  Variables

        Default variables used to customize the deployment.

************************************************************************************************************************************************/

variable "azure_region" {
  description = "Region to create all the resources in."
}

variable "environment" {
  description = "Environment can be PoC, test, stage, prod"
}

variable "project" {
  description = "Name of Project"
}