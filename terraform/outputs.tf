output "resource_group" {
  value = azurerm_resource_group.this.name
}

output "namespace_id" {
  value = azurerm_eventhub_namespace.this.id
}

# Everything the producer, consumer and `make health` need. No secrets:
# authentication is Entra ID (DefaultAzureCredential), so there is nothing to hand out.
output "app_env" {
  value = {
    EVENTHUB_FQDN          = "${azurerm_eventhub_namespace.this.name}.servicebus.windows.net"
    EVENTHUB_NAME          = azurerm_eventhub.orders.name
    EVENTHUB_NAMESPACE_ID  = azurerm_eventhub_namespace.this.id
    EVENTHUB_TU            = tostring(var.throughput_units)
    CONSUMER_GROUP         = azurerm_eventhub_consumer_group.processor.name
    CHECKPOINT_ACCOUNT_URL = azurerm_storage_account.checkpoints.primary_blob_endpoint
    CHECKPOINT_CONTAINER   = azurerm_storage_container.checkpoints.name
  }
}
