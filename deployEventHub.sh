#!/bin/bash
#
# This script is in two parts; Event Hub Environment Deployment and Post-Deployment Configuration.
#
#   Part 1: Event Hub Environment Deployment
#
#       This is simply validation that the Terraform deployment was completed before executing the post-deployment 
#       configuration.
#
#   This script should be executed via the Azure Cloud Shell via:
#
#       @Azure:~/Azure-Event-Hub-PoC/$ bash deployEventHub.sh
#
#   To destroy resources 
#       @Azure: cd Terraform
#       @Azure: terraform destroy
#
# Todo:
#    - Bicep deployment


#
# Part 1: Event Hub Environment Deployment
#

# Make sure this configuration script hasn't been executed already
if [ -f "deployEvent Hub.complete" ]; then
    echo "ERROR: It appears this configuration has already been completed." | tee -a deployEvent Hub.log
    exit 1;
fi

# Try and determine if we're executing from within the Azure Cloud Shell
if [ ! "${AZUREPS_HOST_ENVIRONMENT}" = "cloud-shell/1.0" ]; then
    echo "ERROR: It doesn't appear like your executing this from the Azure Cloud Shell. Please use the Azure Cloud Shell at https://shell.azure.com" | tee -a deployEvent Hub.log
    exit 1;
fi

aadToken=$(az account get-access-token --resource=https://eventhubs.azure.net/ --query accessToken --output tsv 2>&1)
if echo "$aadToken" | grep -q "ERROR"; then
    echo "ERROR: You don't appear to be logged in to Azure CLI. Please login to the Azure CLI using 'az login'" | tee -a deployEventHub.log
    exit 1;
fi

# The token has been successfully received, now you can use it to access the Event Hubs
echo "Successfully logged in to Azure CLI and obtained an access token for Azure Event Hubs."

# Get environment details
azureSubscriptionName=$(az account show --query name --output tsv 2>&1)
azureSubscriptionID=$(az account show --query id --output tsv 2>&1)
azureUsername=$(az account show --query user.name --output tsv 2>&1)
# azureUsernameObjectId=$(az ad user show --id $azureUsername --query objectId --output tsv 2>&1)

# Update a few Terraform variables if they aren't configured by the user
# sed -i "s/REPLACE_Event Hub_AZURE_AD_ADMIN_UPN/${azureUsername}/g" Terraform/terraform.tfvars

        deploymentType="terraform"
        echo "Deploying Event Hub environment. This will take several minutes..." | tee -a deployEventHub.log

        # Terraform init and validation
        echo "Executing 'terraform -chdir=Terraform init'"
        terraformInit=$(terraform -chdir=Terraform init 2>&1)
        if ! echo "$terraformInit" | grep -q "Terraform has been successfully initialized!"; then
            echo "ERROR: Failed to perform 'terraform -chdir=Terraform init'" | tee -a deployEvent Hub.log
            exit 1;
        fi

        # Terraform plan and validation
        echo "Executing 'terraform -chdir=Terraform plan'"
        terraformPlan=$(terraform -chdir=Terraform plan)
        if echo "$terraformPlan" | grep -q "Error:"; then
            echo "ERROR: Failed to perform 'terraform -chdir=Terraform plan'" | tee -a deployEvent Hub.log
            exit 1;
        fi

        # Terraform apply and validation
        echo "Executing 'terraform -chdir=Terraform apply'"
        terraformApply=$(terraform -chdir=Terraform apply -auto-approve)
        if echo "$terraformApply" | grep -q "Apply complete!"; then
            deploymentType="terraform"
        else
            echo "ERROR: Failed to perform 'terraform -chdir=Terraform apply'" | tee -a deployEvent Hub.log
            exit 1;
        fi