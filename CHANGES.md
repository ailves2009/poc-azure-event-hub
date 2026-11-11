# Changes: 2023 → 2026 review

The 2023 version deployed a Basic namespace with a shared access policy and sample scripts.
A review in November 2026 found the issues below. Each fix is in the code, and the ones that
could come back are enforced by [policy/guardrails.py](policy/guardrails.py) or tests.

## Critical

| # | Finding | Fix | Enforced by |
| - | ------- | --- | ----------- |
| 1 | A real SAS connection string was committed in a sample script, in a public repository | File purged from the whole git history (`git filter-repo`); key-based auth removed entirely (local auth off, storage keys off); the namespace it belonged to no longer exists | `no_sas_policies`, `namespace_entra_only`, `storage_no_keys` |
| 2 | `deployEventHub.sh` captured `terraform plan` without stderr and grepped for `Error:`, so a failed plan went on to `apply` | Script replaced by a Makefile with `set -euo pipefail`; `apply` runs the saved, reviewed plan | `make up` = `plan -out` + `apply tfplan` |
| 3 | CI installed a `requirements.txt` that did not exist and ran no Terraform steps | GitHub Actions: fmt, validate, tflint, Checkov, guardrails, tests, ruff; optional plan + AI review | `.github/workflows/ci.yml` |

## Terraform

| # | Finding | Fix |
| - | ------- | --- |
| 4 | `sku = "Basic"`: no consumer groups, Kafka, IP filter or Capture, contradicting the design | Standard, 1 TU, auto-inflate off (`namespace_cost_bounded`) |
| 5 | One SAS rule with listen + send | Separate Sender / Receiver RBAC roles scoped to the event hub (`least_privilege_roles`) |
| 6 | Hard-coded global names; `random_string` declared but unused | Names use the random suffix |
| 7 | `partition_count`, `message_retention` variables declared but ignored | Used, typed, validated against Standard limits |
| 8 | azurerm `~> 2.79` (2021), unused `azuread` provider and data source, `random` not pinned | azurerm `~> 5.13`, random `~> 3.9`, unused parts removed |
| 9 | No TLS minimum, no diagnostics, no alerts, no budget | TLS 1.2, Log Analytics, alerts on throttling and server errors, monthly budget |
| 10 | `terraform fmt` failed | Formatted, checked in CI |

## Application

| # | Finding | Fix |
| - | ------- | --- |
| 11 | Connection strings in code | `DefaultAzureCredential` (az login / managed identity) |
| 12 | `update_checkpoint` without a checkpoint store: progress lost on restart | Blob checkpoint store, periodic + shutdown checkpoints |
| 13 | No partition key: no ordering guarantee per customer | `customer_id` as partition key, batches per key |
| 14 | Two duplicate send scripts, no `requirements.txt`, broad `except Exception` | One producer, pinned dependencies, catches only the batch-full `ValueError` |
| 15 | No way to see consumer lag | `health.py`: lag per partition + metrics + verdicts |
| 16 | The Kafka endpoint, the main reason to pick Event Hubs over a queue, was never shown | `kafka_consumer.py`: plain librdkafka client, Entra ID via OAUTHBEARER |

## Documentation

| # | Finding | Fix |
| - | ------- | --- |
| 17 | README called hard-coded values "best practices"; no decision, security or cost sections | README in the series format |
| 18 | Factual errors on the 2023 slides | [docs/slides-2023-errata.md](docs/slides-2023-errata.md) |
