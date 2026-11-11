plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "azurerm" {
  enabled = true
  version = "0.31.1"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

# This POC is built and destroyed in one sitting (`make up` ... `make down`);
# prevent_destroy would block the teardown that keeps it cheap. Production stacks keep this rule on.
rule "azurerm_resources_missing_prevent_destroy" {
  enabled = false
}
