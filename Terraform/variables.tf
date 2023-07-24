/************************************************************************************************************************************************

  Variables

        Default variables used to customize the deployment.

************************************************************************************************************************************************/

variable "azure_region" {
  description = "Region to create all the resources in."
}

variable "environment" {
  description = "Proof of Concept environment"
}

variable "project" {
  description = "Azure Event Hub PoC"
}

variable "partition_count" {
  description = "Number of partitions in Event Hub"
}

variable "message_retention" {
  description = "Retention period for store massages in Event Hub"
}
