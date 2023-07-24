/************************************************************************************************************************************************

  Custom Configuration

        Most of the configurations you will want to change for a functional PoC are located here. While you can modify any part of the 
        deployment, you must configure these to fit your existing Azure environment.

************************************************************************************************************************************************/

azure_region        = "westeurope"       // Region to create all the resources in.
environment         = "PoC"              // Proof of Concept environment
project             = "Azure Event Hub"  // Azure Event Hub PoC
partition_count     = 2                  // Number of partitions in Event Hub
message_retention   = 1                  // retention period for store massages in Event Hub