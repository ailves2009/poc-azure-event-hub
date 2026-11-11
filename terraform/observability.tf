# Observability as code: logs and metrics go to Log Analytics, and the two signals
# that matter most for an ingestion service raise an alert:
# - ThrottledRequests: producers hit the throughput-unit limit (scale or batch);
# - ServerErrors: the service itself is failing.
# Consumer lag is not an Azure metric; `make health` computes it from checkpoints.

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${local.name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags

  sku               = "PerGB2018"
  retention_in_days = 30
  daily_quota_gb    = 0.5 # cost guard: a noisy POC cannot run up the ingestion bill
}

resource "azurerm_monitor_diagnostic_setting" "namespace" {
  name                       = "to-log-analytics"
  target_resource_id         = azurerm_eventhub_namespace.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_action_group" "owner" {
  count = var.alert_email == "" ? 0 : 1

  name                = "ag-${local.name}"
  resource_group_name = azurerm_resource_group.this.name
  short_name          = "evh-poc"
  tags                = local.tags

  email_receiver {
    name                    = "owner"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

locals {
  alerts = {
    throttled = {
      metric      = "ThrottledRequests"
      severity    = 2
      description = "Producers are throttled: throughput units are exhausted. Batch sends or add a TU."
    }
    server_errors = {
      metric      = "ServerErrors"
      severity    = 1
      description = "Event Hubs returns server errors. Check Azure status and retry policy."
    }
  }
}

resource "azurerm_monitor_metric_alert" "namespace" {
  for_each = local.alerts

  name                = "alert-${local.name}-${each.key}"
  resource_group_name = azurerm_resource_group.this.name
  scopes              = [azurerm_eventhub_namespace.this.id]
  description         = each.value.description
  severity            = each.value.severity
  frequency           = "PT5M"
  window_size         = "PT5M"
  tags                = local.tags

  criteria {
    metric_namespace = "Microsoft.EventHub/namespaces"
    metric_name      = each.value.metric
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  dynamic "action" {
    for_each = azurerm_monitor_action_group.owner
    content {
      action_group_id = action.value.id
    }
  }
}
