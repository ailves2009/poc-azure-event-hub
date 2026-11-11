"""Policy as code for terraform/*.tf: the findings of the 2023 -> 2026 review, encoded
so the same mistakes cannot come back in a pull request.

Run: python policy/guardrails.py terraform   (exit 1 on any violation)
Each rule returns human-readable violations; CI fails on any of them.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import hcl2

Resource = tuple[str, str, dict]  # (type, name, attributes)

FORBIDDEN_ROLES = {"Owner", "Contributor", "Azure Event Hubs Data Owner", "Storage Blob Data Owner"}
ALLOWED_EVENTHUB_SKUS = {"Standard"}  # Premium/Dedicated start at hundreds of USD per month


def _unquote(value):
    if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def load_resources(tf_dir: Path) -> list[Resource]:
    resources: list[Resource] = []
    for path in sorted(tf_dir.glob("*.tf")):
        with path.open() as fh:
            doc = hcl2.load(fh)
        for block in doc.get("resource", []):
            for rtype, named in block.items():
                for rname, attrs in named.items():
                    resources.append((_unquote(rtype), _unquote(rname), attrs))
    return resources


def _of_type(resources: list[Resource], rtype: str) -> Iterator[tuple[str, dict]]:
    for t, name, attrs in resources:
        if t == rtype:
            yield f"{t}.{name}", attrs


def no_sas_policies(resources: list[Resource]) -> list[str]:
    sas = {
        "azurerm_eventhub_authorization_rule",
        "azurerm_eventhub_namespace_authorization_rule",
        "azurerm_storage_account_sas",
    }
    return [f"{t}.{n}: SAS keys are not allowed, use Entra ID RBAC" for t, n, _ in resources if t in sas]


def namespace_entra_only(resources: list[Resource]) -> list[str]:
    return [
        f"{addr}: local_authentication_enabled must be false"
        for addr, a in _of_type(resources, "azurerm_eventhub_namespace")
        if a.get("local_authentication_enabled") is not False
    ]


def namespace_tls12(resources: list[Resource]) -> list[str]:
    return [
        f"{addr}: minimum_tls_version must be 1.2"
        for addr, a in _of_type(resources, "azurerm_eventhub_namespace")
        if _unquote(a.get("minimum_tls_version")) != "1.2"
    ]


def namespace_cost_bounded(resources: list[Resource]) -> list[str]:
    out = []
    for addr, a in _of_type(resources, "azurerm_eventhub_namespace"):
        if _unquote(a.get("sku")) not in ALLOWED_EVENTHUB_SKUS:
            out.append(f"{addr}: sku must be one of {sorted(ALLOWED_EVENTHUB_SKUS)} in this POC")
        if a.get("auto_inflate_enabled") is not False:
            out.append(f"{addr}: auto_inflate_enabled must be false (unbounded cost)")
    return out


def storage_no_keys(resources: list[Resource]) -> list[str]:
    out = []
    for addr, a in _of_type(resources, "azurerm_storage_account"):
        if a.get("shared_access_key_enabled") is not False:
            out.append(f"{addr}: shared_access_key_enabled must be false")
        if a.get("allow_nested_items_to_be_public") is not False:
            out.append(f"{addr}: allow_nested_items_to_be_public must be false")
        if _unquote(a.get("min_tls_version")) != "TLS1_2":
            out.append(f"{addr}: min_tls_version must be TLS1_2")
    return out


def least_privilege_roles(resources: list[Resource]) -> list[str]:
    out = []
    for addr, a in _of_type(resources, "azurerm_role_assignment"):
        role = _unquote(a.get("role_definition_name"))
        if role in FORBIDDEN_ROLES:
            out.append(f"{addr}: role '{role}' is broader than this workload needs")
        scope = str(a.get("scope", ""))
        if "subscription" in scope or "resource_group" in scope:
            out.append(f"{addr}: scope the role to the event hub / container, not {scope}")
    return out


def everything_tagged(resources: list[Resource]) -> list[str]:
    # Resources that support tags and carry cost must be attributable (FinOps).
    taggable = {
        "azurerm_resource_group",
        "azurerm_eventhub_namespace",
        "azurerm_storage_account",
        "azurerm_log_analytics_workspace",
    }
    return [f"{t}.{n}: missing tags" for t, n, a in resources if t in taggable and "tags" not in a]


RULES: list[Callable[[list[Resource]], list[str]]] = [
    no_sas_policies,
    namespace_entra_only,
    namespace_tls12,
    namespace_cost_bounded,
    storage_no_keys,
    least_privilege_roles,
    everything_tagged,
]


def check(tf_dir: Path) -> list[str]:
    resources = load_resources(tf_dir)
    return [violation for rule in RULES for violation in rule(resources)]


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "terraform")
    violations = check(target)
    for v in violations:
        print(f"DENY {v}")
    print(f"{len(RULES)} rules, {len(violations)} violations")
    sys.exit(1 if violations else 0)
