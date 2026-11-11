from plan_facts import facts


def rc(address, actions, after=None, after_unknown=None):
    return {
        "address": address,
        "type": address.split(".")[0],
        "change": {"actions": actions, "before": None, "after": after, "after_unknown": after_unknown or {}},
    }


SECURE_NAMESPACE = {
    "sku": "Standard",
    "capacity": 1,
    "auto_inflate_enabled": False,
    "local_authentication_enabled": False,
    "minimum_tls_version": "1.2",
    "public_network_access_enabled": True,
    "network_rulesets": [{"default_action": "Deny"}],
}
SENDER = {"role_definition_name": "Azure Event Hubs Data Sender"}
CAPTURE_ON = {"partition_count": 4, "capture_description": [{"enabled": True}]}
BUDGET = rc("azurerm_consumption_budget_resource_group.this", ["create"], {"amount": 30})


def test_secure_environment_has_no_warnings():
    plan = {
        "resource_changes": [
            rc("azurerm_eventhub_namespace.this", ["create"], SECURE_NAMESPACE),
            rc("azurerm_role_assignment.producer_send", ["create"], SENDER),
            BUDGET,
        ]
    }
    f = facts(plan)
    assert f["summary"]["create"] == 3
    assert f["warnings"] == []
    assert f["access"][0]["role"] == "Azure Event Hubs Data Sender"
    assert f["cost_drivers"]["throughput_units"] == 1


def test_2023_style_environment_is_called_out():
    ns = {**SECURE_NAMESPACE, "local_authentication_enabled": True, "network_rulesets": None}
    plan = {
        "resource_changes": [
            rc("azurerm_eventhub_namespace.ns", ["create"], ns, {"network_rulesets": True}),
            rc("azurerm_eventhub_authorization_rule.rule", ["create"], {"listen": True, "send": True}),
        ]
    }
    w = "\n".join(facts(plan)["warnings"])
    assert "local (SAS) authentication is enabled" in w
    assert "reachable from any IP" in w
    assert "SAS key policy" in w
    assert "no budget" in w


def test_capture_and_extra_tu_are_cost_warnings():
    plan = {
        "resource_changes": [
            rc("azurerm_eventhub_namespace.this", ["update"], {**SECURE_NAMESPACE, "capacity": 2}),
            rc("azurerm_eventhub.orders", ["update"], CAPTURE_ON),
            BUDGET,
        ]
    }
    f = facts(plan)
    assert f["cost_drivers"]["capture_enabled"] is True
    assert any("2 throughput units" in w for w in f["warnings"])
    assert any("Capture enabled" in w for w in f["warnings"])


def test_replacing_event_hub_is_flagged():
    plan = {"resource_changes": [rc("azurerm_eventhub.orders", ["delete", "create"], {}), BUDGET]}
    f = facts(plan)
    assert f["replaces"] == ["azurerm_eventhub.orders"]
    assert any("stateful resource replaced" in w for w in f["warnings"])


def test_no_ops_are_ignored():
    plan = {"resource_changes": [rc("azurerm_resource_group.this", ["no-op"], {})]}
    assert facts(plan)["summary"] == {"create": 0, "update": 0, "replace": 0, "delete": 0}
