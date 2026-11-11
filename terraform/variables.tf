variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "westeurope"
}

variable "prefix" {
  description = "Short name prefix; a random suffix is added for global uniqueness."
  type        = string
  default     = "evhpoc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,9}$", var.prefix))
    error_message = "prefix: 3-10 lowercase letters/digits, starting with a letter."
  }
}

variable "environment" {
  description = "Environment tag."
  type        = string
  default     = "poc"
}

variable "owner" {
  description = "Owner tag: who to ask before deleting this."
  type        = string
  default     = "platform-team"
}

variable "throughput_units" {
  description = "Event Hubs Standard throughput units. 1 TU = 1 MB/s or 1000 events/s in, 2 MB/s out."
  type        = number
  default     = 1

  validation {
    # Cost guard for a POC: each TU is a fixed hourly charge.
    condition     = var.throughput_units >= 1 && var.throughput_units <= 2
    error_message = "throughput_units: 1-2 in this POC. Raise the limit consciously, not by accident."
  }
}

variable "partition_count" {
  description = "Partitions of the orders event hub. Immutable on Standard; caps consumer parallelism."
  type        = number
  default     = 4

  validation {
    condition     = var.partition_count >= 1 && var.partition_count <= 32
    error_message = "partition_count: 1-32 on the Standard tier."
  }
}

variable "message_retention_days" {
  description = "How long events stay readable (replay window)."
  type        = number
  default     = 1

  validation {
    condition     = var.message_retention_days >= 1 && var.message_retention_days <= 7
    error_message = "message_retention_days: 1-7 on the Standard tier."
  }
}

variable "allowed_cidrs" {
  description = "Optional IP allowlist for the namespace (e.g. [\"203.0.113.10/32\"]). Empty = no IP filter."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for c in var.allowed_cidrs : can(cidrhost(c, 0))])
    error_message = "allowed_cidrs: every entry must be a CIDR, e.g. 203.0.113.10/32."
  }
}

variable "producer_principal_id" {
  description = "Object ID that gets 'Data Sender'. Null = the identity running Terraform."
  type        = string
  default     = null
}

variable "consumer_principal_id" {
  description = "Object ID that gets 'Data Receiver' and checkpoint access. Null = the identity running Terraform."
  type        = string
  default     = null
}

variable "alert_email" {
  description = "Email for alerts and budget notifications. Empty = subscription Owners only, no alert emails."
  type        = string
  default     = ""
}

variable "monthly_budget_usd" {
  description = "Monthly budget for the resource group, USD."
  type        = number
  default     = 30
}

variable "capture_enabled" {
  description = "Archive all events to Blob (Avro) with Event Hubs Capture. Billed per TU-hour on Standard."
  type        = bool
  default     = false
}
