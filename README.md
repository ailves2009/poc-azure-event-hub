# Azure Event Hub PoC

![alt tag](https://github.com/iag2009/Azure-Event-Hub-PoC/tree/master/Images/Azure_Event_Hub_common.png)

# Description

Create an Event Hub environment based on best practices to achieve a successful proof of concept. 

# How to Run

### "Easy Button" Deployment
The following commands should be executed from the Azure Cloud Shell at https://shell.azure.com using bash:
```
@Azure:~$ git clone https://github.com/iag2009/Azure-Event-Hub-PoC
@Azure:~$ cd Azure-Event-Hub-PoC
@Azure:~$ bash deployEventHub.sh
```

### Advanced Deployment: Terraform
You can manually configure the Terraform parameters and update default settings such as the Azure region and other. The following commands should be executed from the Azure Cloud Shell at https://shell.azure.com using bash:
```
@Azure:~$ git clone https://github.com/iag2009/Azure-Event-Hub-PoC
@Azure:~$ cd Azure-Event-Hub-PoC
@Azure:~$ code Terraform/terraform.tfvars
@Azure:~$ terraform -chdir=Terraform init
@Azure:~$ terraform -chdir=Terraform plan
@Azure:~$ terraform -chdir=Terraform apply
@Azure:~$ bash deployEventHub.sh 
```

# What's Deployed

### Azure Event Hub Namespace
- <b>eventhub-ns-da-poc</b> - container that provides logical separation and management of multiple Event Hubs in Azure subscription.

### Azure Event Hub
- <b>Eventhub1-poc</b> - a managed event streaming service in the Microsoft Azure cloud.

# What's Configured
Azure Resource Group
- <b>eventhub-rg-poc</b>

# To Do
- Dive into Stream Analysis
- Bicep deployment

