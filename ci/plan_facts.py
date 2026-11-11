"""Deterministic posture facts from `terraform show -json tfplan` for the AI plan reviewer.

CI plans against empty state (the POC has no shared state: `make up` creates it,
`make down` removes it), so the plan is the full environment. The facts describe it:
who gets access, how exposed it is, whether keys exist, what drives the bill, and
deterministic warnings. The model explains these facts; it does not produce them.

Usage: python ci/plan_facts.py plan.json > facts.json
"""

from __future__ import annotations

import json
import sys

SAS_TYPES = {"azurerm_eventhub_authorization_rule", "azurerm_eventhub_namespace_authorization_rule"}


def _after(rc: dict) -> dict:
    return rc["change"].get("after") or {}


def _unknown(rc: dict, attr: str) -> bool:
    return bool((rc["change"].get("after_unknown") or {}).get(attr))


def facts(plan: dict) -> dict:
    summary = {"create": 0, "update": 0, "replace": 0, "delete": 0}
    replaces, deletes, access, keys, exposure, cost, warnings = [], [], [], [], {}, {}, []

    for rc in plan.get("resource_changes", []):
        actions = rc["change"]["actions"]
        if actions in (["no-op"], ["read"]):
            continue
        addr, rtype, after = rc["address"], rc["type"], _after(rc)

        if "delete" in actions and "create" in actions:
            summary["replace"] += 1
            replaces.append(addr)
        elif actions == ["delete"]:
            summary["delete"] += 1
            deletes.append(addr)
            continue
        elif actions == ["create"]:
            summary["create"] += 1
        else:
            summary["update"] += 1

        if rtype == "azurerm_role_assignment":
            access.append({"address": addr, "role": after.get("role_definition_name")})
            if after.get("role_definition_name") in {"Owner", "Contributor", "Azure Event Hubs Data Owner"}:
                warnings.append(f"{addr}: broad role {after.get('role_definition_name')}")

        if rtype in SAS_TYPES:
            keys.append(addr)
            warnings.append(f"{addr}: SAS key policy, keys can leak and must be rotated")

        if rtype == "azurerm_eventhub_namespace":
            ip_filter = "set" if after.get("network_rulesets") else "none"
            if _unknown(rc, "network_rulesets") and not after.get("network_rulesets"):
                ip_filter = "none"  # computed default: no rules were configured
            exposure = {
                "public_network_access_enabled": after.get("public_network_access_enabled"),
                "ip_filter": ip_filter,
                "local_authentication_enabled": after.get("local_authentication_enabled"),
                "minimum_tls_version": after.get("minimum_tls_version"),
            }
            cost.update(
                {
                    "sku": after.get("sku"),
                    "throughput_units": after.get("capacity"),
                    "auto_inflate_enabled": after.get("auto_inflate_enabled"),
                }
            )
            if after.get("local_authentication_enabled") is not False:
                warnings.append(f"{addr}: local (SAS) authentication is enabled")
            if ip_filter == "none" and after.get("public_network_access_enabled"):
                warnings.append(f"{addr}: reachable from any IP (Entra ID still required); set allowed_cidrs")
            if (after.get("capacity") or 0) > 1:
                warnings.append(f"{addr}: {after.get('capacity')} throughput units, each is a fixed hourly charge")

        if rtype == "azurerm_eventhub":
            capture = bool(after.get("capture_description"))
            cost["capture_enabled"] = capture
            cost["partition_count"] = after.get("partition_count")
            if capture:
                warnings.append(f"{addr}: Capture enabled, billed per TU-hour on Standard")

        if rtype == "azurerm_storage_account" and after.get("shared_access_key_enabled") is not False:
            keys.append(addr)
            warnings.append(f"{addr}: storage account keys enabled")

        if rtype == "azurerm_log_analytics_workspace":
            cost["log_analytics_daily_quota_gb"] = after.get("daily_quota_gb")

        if rtype == "azurerm_consumption_budget_resource_group":
            cost["monthly_budget"] = after.get("amount")

    for addr in replaces + deletes:
        if addr.split(".")[0] in {"azurerm_eventhub_namespace", "azurerm_eventhub", "azurerm_storage_account"}:
            warnings.append(f"{addr}: stateful resource replaced or deleted (new FQDN, lost events or checkpoints)")

    if "monthly_budget" not in cost:
        warnings.append("no budget in this plan")

    return {
        "summary": summary,
        "replaces": replaces,
        "deletes": deletes,
        "access": access,
        "key_based_auth": keys,
        "exposure": exposure,
        "cost_drivers": cost,
        "warnings": warnings,
    }


if __name__ == "__main__":
    with open(sys.argv[1]) as fh:
        json.dump(facts(json.load(fh)), sys.stdout, indent=2)
    print()
