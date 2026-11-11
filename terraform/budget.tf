# FinOps guardrail: a monthly budget on the POC resource group.
# A budget does not stop spending; it tells a human early. The real cost control
# is `make down` and the fixed throughput (no auto-inflate) in main.tf.

resource "azurerm_consumption_budget_resource_group" "this" {
  name              = "budget-${local.name}"
  resource_group_id = azurerm_resource_group.this.id
  amount            = var.monthly_budget_usd
  time_grain        = "Monthly"

  time_period {
    # Budgets must start on the first day of a month.
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", plantimestamp())
  }

  notification {
    enabled        = true
    operator       = "GreaterThan"
    threshold      = 50
    threshold_type = "Actual"
    contact_emails = var.alert_email == "" ? [] : [var.alert_email]
    contact_roles  = ["Owner"]
  }

  notification {
    enabled        = true
    operator       = "GreaterThan"
    threshold      = 100
    threshold_type = "Forecasted"
    contact_emails = var.alert_email == "" ? [] : [var.alert_email]
    contact_roles  = ["Owner"]
  }

  lifecycle {
    ignore_changes = [time_period] # plantimestamp() changes on every plan
  }
}
