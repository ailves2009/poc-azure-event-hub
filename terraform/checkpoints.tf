# One Entra-only storage account, two containers:
# - checkpoints: where each partition was last processed up to. Without a durable
#   store a restarted consumer re-reads everything, or skips data;
# - capture (optional): the Event Hubs Capture archive.

resource "azurerm_storage_account" "checkpoints" {
  #checkov:skip=CKV_AZURE_33:No queues in this account; blob access is logged (see diagnostic setting below)
  #checkov:skip=CKV_AZURE_206:LRS on purpose: checkpoints are rebuildable state, GRS doubles the price
  #checkov:skip=CKV_AZURE_59:POC consumers run from a laptop; data plane is Entra-only. Production: private endpoint
  #checkov:skip=CKV2_AZURE_33:Private endpoint is listed under "Not done in this POC" in the README
  #checkov:skip=CKV2_AZURE_1:Platform-managed keys; CMK is a compliance decision, listed under "Not done"
  name                = "stckpt${random_string.suffix.result}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags

  account_tier             = "Standard"
  account_replication_type = "LRS" # checkpoints are rebuildable state; GRS is not worth the price here

  shared_access_key_enabled       = false # Entra ID only, same as the namespace
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true

  blob_properties {
    delete_retention_policy {
      days = 7 # a bad deploy or script cannot silently wipe checkpoints or the archive
    }
    container_delete_retention_policy {
      days = 7
    }
  }
}

# Audit trail: who read, wrote or deleted checkpoints and archive blobs.
resource "azurerm_monitor_diagnostic_setting" "blob" {
  name                       = "to-log-analytics"
  target_resource_id         = "${azurerm_storage_account.checkpoints.id}/blobServices/default"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  enabled_log {
    category = "StorageRead"
  }
  enabled_log {
    category = "StorageWrite"
  }
  enabled_log {
    category = "StorageDelete"
  }
}

resource "azurerm_storage_container" "checkpoints" {
  #checkov:skip=CKV2_AZURE_21:Blob read/write/delete logs are on, see azurerm_monitor_diagnostic_setting.blob (graph check misses it)
  name                  = "checkpoints"
  storage_account_id    = azurerm_storage_account.checkpoints.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "capture" {
  #checkov:skip=CKV2_AZURE_21:Blob read/write/delete logs are on, see azurerm_monitor_diagnostic_setting.blob (graph check misses it)
  count = var.capture_enabled ? 1 : 0

  name                  = "capture"
  storage_account_id    = azurerm_storage_account.checkpoints.id
  container_access_type = "private"
}
