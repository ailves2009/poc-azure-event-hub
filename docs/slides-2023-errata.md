# Errata: 2023 slides

[slides-2023.key](slides-2023.key) is kept as the original talk. These corrections apply to it.

| Slide | Says | Correct |
| ----- | ---- | ------- |
| Networking (Private) | Private DNS `name.dev.azureeventhub.net` | The namespace is `<namespace>.servicebus.windows.net`; with a private endpoint it resolves through the private DNS zone `privatelink.servicebus.windows.net`. Storage uses `privatelink.blob.core.windows.net` and `privatelink.dfs.core.windows.net` |
| Networking (Public) | Use `RootManageSharedAccessKey` in the application | Never give an application the root key (it includes Manage). Disable local auth and grant `Azure Event Hubs Data Sender` / `Data Receiver` with Entra ID |
| Networking (Public) | Step numbering 1, 2, 3, 3, 4, 5 | 1-6 |
| Networking (Public) | IP allowlist, firewall | IP filtering requires Standard or higher; the deployed Basic namespace did not support it |
| Networking (Public) | Ports 5671 and 443 | Also 5672 (AMQP without TLS, should stay closed) and 9093 for the Kafka endpoint (Standard and higher) |
| Authentication | "SAS is the primary means for authentication" | Microsoft recommends Microsoft Entra ID (formerly Azure Active Directory) with RBAC; SAS is for cases where Entra ID is not possible |
| Overview / Features | Protocols: HTTP and AMQP | Plus the Apache Kafka protocol (Standard and higher), shown on the diagram but missing from the text |
| Overview / Pricing | Basic for $11/month | Basic lacks consumer groups, Kafka, IP filtering and Capture. Standard (~$22/month per TU) is the realistic minimum. The pipeline's largest cost, Stream Analytics (~$80/month per streaming unit, 24/7), was not counted |
| Logging, Monitoring | Capture "transforms and analyses telemetry in real time" | Capture is a batch archive to Blob or Data Lake (Avro, or Parquet via Stream Analytics) on a time/size window. Real-time processing is done by consumers or Stream Analytics. Capture also requires Standard or higher |
| Advanced Deployment | `sku = "Basic"`, SAS rule, `deployEventHub.sh` | See [CHANGES.md](../CHANGES.md): Standard, Entra ID only, Makefile with a saved plan |
| Thank you | Former employer and corporate email | Outdated contact details; not to be used |
