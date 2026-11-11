# Data-plane access. Least privilege:
# - roles are scoped to the single event hub / container, never the namespace or account;
# - Sender and Receiver are separate roles, so producers cannot read and consumers cannot write;
# - no "Data Owner", no Contributor.
#
# In the POC both principals default to whoever runs Terraform, so the demo works
# from a laptop or Cloud Shell. In production they are two different workload
# identities (managed identity / AKS workload identity) passed in as variables.

locals {
  producer_principal_id = coalesce(var.producer_principal_id, data.azurerm_client_config.current.object_id)
  consumer_principal_id = coalesce(var.consumer_principal_id, data.azurerm_client_config.current.object_id)
}

resource "azurerm_role_assignment" "producer_send" {
  scope                = azurerm_eventhub.orders.id
  role_definition_name = "Azure Event Hubs Data Sender"
  principal_id         = local.producer_principal_id
}

resource "azurerm_role_assignment" "consumer_receive" {
  scope                = azurerm_eventhub.orders.id
  role_definition_name = "Azure Event Hubs Data Receiver"
  principal_id         = local.consumer_principal_id
}

resource "azurerm_role_assignment" "consumer_checkpoints" {
  scope                = azurerm_storage_container.checkpoints.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.consumer_principal_id
}

# Capture writes with the namespace's managed identity, scoped to its own container.
resource "azurerm_role_assignment" "capture_writer" {
  count = var.capture_enabled ? 1 : 0

  scope                = azurerm_storage_container.capture[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_eventhub_namespace.this.identity[0].principal_id
}
