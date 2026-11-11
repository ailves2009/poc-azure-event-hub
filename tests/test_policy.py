"""The guardrails pass on the real code and fire on the mistakes they exist to stop."""

from pathlib import Path

import pytest

import guardrails

ROOT = Path(__file__).resolve().parent.parent


def test_repository_terraform_is_compliant():
    assert guardrails.check(ROOT / "terraform") == []


# The 2023 version of this project, reduced to the parts the rules look at.
BAD_2023 = """
resource "azurerm_resource_group" "rg" {
  name     = "eventhub-rg-poc"
  location = "westeurope"
}

resource "azurerm_eventhub_namespace" "ns" {
  name     = "eventhub-ns-da-poc"
  sku      = "Basic"
  capacity = 2
}

resource "azurerm_eventhub_authorization_rule" "rule" {
  name   = "eventhub-poc-policy"
  listen = true
  send   = true
}

resource "azurerm_eventhub_namespace" "premium" {
  name                         = "big"
  sku                          = "Premium"
  auto_inflate_enabled         = true
  local_authentication_enabled = false
  minimum_tls_version          = "1.2"
  tags                         = {}
}

resource "azurerm_storage_account" "sa" {
  name                            = "st"
  shared_access_key_enabled       = true
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_0"
  tags                            = {}
}

resource "azurerm_role_assignment" "too_broad" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Azure Event Hubs Data Owner"
  principal_id         = "00000000-0000-0000-0000-000000000000"
}
"""


@pytest.fixture
def bad_dir(tmp_path):
    (tmp_path / "main.tf").write_text(BAD_2023)
    return tmp_path


@pytest.mark.parametrize(
    "expected",
    [
        "azurerm_eventhub_authorization_rule.rule: SAS keys are not allowed",
        "azurerm_eventhub_namespace.ns: local_authentication_enabled must be false",
        "azurerm_eventhub_namespace.ns: minimum_tls_version must be 1.2",
        "azurerm_eventhub_namespace.premium: sku must be one of",
        "azurerm_eventhub_namespace.premium: auto_inflate_enabled must be false",
        "azurerm_storage_account.sa: shared_access_key_enabled must be false",
        "azurerm_storage_account.sa: min_tls_version must be TLS1_2",
        "azurerm_role_assignment.too_broad: role 'Azure Event Hubs Data Owner'",
        "azurerm_role_assignment.too_broad: scope the role",
        "azurerm_resource_group.rg: missing tags",
    ],
)
def test_rule_fires(bad_dir, expected):
    violations = guardrails.check(bad_dir)
    assert any(v.startswith(expected) for v in violations), violations
