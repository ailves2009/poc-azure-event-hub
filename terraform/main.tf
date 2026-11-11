# Event ingestion core: one namespace, one event hub, one consumer group.
#
# Decisions (see README, "The decision in one page"):
# - Standard tier: the cheapest tier with consumer groups, Kafka endpoint,
#   IP filtering and 7-day retention. Basic has none of these.
# - Entra ID only: local (SAS) authentication is disabled, so there are no keys
#   to leak, rotate or store. Access is RBAC on the event hub, not the namespace.
# - Fixed throughput: auto-inflate is off, so the bill cannot grow on its own.

data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  name = "${var.prefix}-${random_string.suffix.result}"

  tags = {
    project     = "poc-azure-event-hub"
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_eventhub_namespace" "this" {
  name                = "evhns-${local.name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags

  sku                  = "Standard"
  capacity             = var.throughput_units
  auto_inflate_enabled = false

  local_authentication_enabled  = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = true

  # Used by Capture to write to Storage without keys.
  identity {
    type = "SystemAssigned"
  }

  # Optional IP allowlist. Empty list = reachable from the internet,
  # but every call still needs an Entra ID token with a data-plane role.
  network_rulesets = length(var.allowed_cidrs) == 0 ? null : [{
    default_action                 = "Deny"
    public_network_access_enabled  = true
    trusted_service_access_enabled = true
    ip_rule                        = [for cidr in var.allowed_cidrs : { ip_mask = cidr, action = "Allow" }]
    virtual_network_rule           = []
  }]
}

resource "azurerm_eventhub" "orders" {
  name         = "orders"
  namespace_id = azurerm_eventhub_namespace.this.id

  # Partitions cannot be changed after creation on the Standard tier:
  # they cap consumer parallelism, so this is the one decision to get right up front.
  partition_count   = var.partition_count
  message_retention = var.message_retention_days

  # Capture: batch archive of every event to Blob (Avro), for replay beyond retention
  # and for analytics. It is not real-time processing. Off by default: on Standard it
  # is billed per TU-hour and costs more than the namespace itself.
  dynamic "capture_description" {
    for_each = var.capture_enabled ? [1] : []
    content {
      enabled             = true
      encoding            = "Avro"
      interval_in_seconds = 300
      size_limit_in_bytes = 314572800
      skip_empty_archives = true

      destination {
        name                        = "EventHubArchive.AzureBlockBlob"
        storage_account_id          = azurerm_storage_account.checkpoints.id
        blob_container_name         = azurerm_storage_container.capture[0].name
        archive_name_format         = "{Namespace}/{EventHub}/{PartitionId}/{Year}/{Month}/{Day}/{Hour}/{Minute}/{Second}"
        storage_authentication_type = "SystemAssigned"
      }
    }
  }

  depends_on = [azurerm_role_assignment.capture_writer]
}

resource "azurerm_eventhub_consumer_group" "processor" {
  name                = "orders-processor"
  namespace_name      = azurerm_eventhub_namespace.this.name
  eventhub_name       = azurerm_eventhub.orders.name
  resource_group_name = azurerm_resource_group.this.name
}
