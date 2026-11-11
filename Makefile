# poc-azure-event-hub: one command per step. Works on macOS, Linux and Azure Cloud Shell.
# Prerequisites: az (logged in), terraform >= 1.9, python >= 3.11.

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

TF      := terraform -chdir=terraform
VENV    := .venv
PY      := $(VENV)/bin/python
APP     := cd app && ../$(PY)

# azurerm needs the subscription explicitly; take the one `az` is logged in to.
export ARM_SUBSCRIPTION_ID ?= $(shell az account show --query id -o tsv 2>/dev/null)

.PHONY: help
help: ## Show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

$(VENV)/.ok: app/requirements.txt requirements-dev.txt
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r requirements-dev.txt
	touch $@

.PHONY: venv
venv: $(VENV)/.ok ## Create the Python virtualenv

.PHONY: check-login
check-login:
	@test -n "$(ARM_SUBSCRIPTION_ID)" || { echo "Not logged in: run 'az login' first."; exit 1; }
	@az account show --query '{subscription:name, user:user.name}' -o tsv

.PHONY: plan
plan: check-login ## terraform plan (saved to terraform/tfplan)
	$(TF) init -input=false -upgrade=false
	$(TF) plan -input=false -out=tfplan

.PHONY: up
up: plan ## Create everything (applies exactly the reviewed plan)
	$(TF) apply -input=false tfplan
	rm -f terraform/tfplan
	$(MAKE) --no-print-directory env
	@echo "Up. Data-plane RBAC can take 1-5 minutes to propagate before 'make demo' works."

.PHONY: env
env: ## Write .env from terraform outputs (endpoints only, no secrets)
	$(TF) output -json app_env | python3 -c 'import json,sys; [print(f"{k}={v}") for k,v in json.load(sys.stdin).items()]' > .env
	@cat .env

.PHONY: send
send: venv ## Send 500 orders (partition key = customer)
	$(APP) producer.py --count 500 --customers 25

.PHONY: receive
receive: venv ## Consume for 30s with Blob checkpoints
	$(APP) consumer.py --duration 30

.PHONY: kafka
kafka: venv ## Read the same event hub with a plain Kafka client (Entra ID, port 9093)
	$(APP) kafka_consumer.py --duration 30

.PHONY: health
health: venv ## Lag, metrics and verdicts as JSON (input for the triage agent)
	$(APP) health.py

.PHONY: demo
demo: send receive kafka health ## send -> receive (SDK) -> receive (Kafka) -> health

.PHONY: lint
lint: venv ## Everything CI runs, offline
	terraform -chdir=terraform fmt -check -recursive
	$(TF) init -backend=false -input=false >/dev/null
	$(TF) validate
	cd terraform && tflint --init >/dev/null && tflint --format compact
	$(VENV)/bin/ruff check . && $(VENV)/bin/ruff format --check .
	$(PY) policy/guardrails.py terraform
	$(VENV)/bin/pytest -q
	@command -v checkov >/dev/null && checkov -d terraform --framework terraform --compact --quiet || echo "checkov not installed: skipped (runs in CI)"

.PHONY: down
down: check-login ## Destroy everything (asks for confirmation)
	$(TF) destroy -input=false
	rm -f .env
