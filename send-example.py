import asyncio
import json
from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData

# add value from /Event Hubs Instance/Shared access policies/[your polycy name]/Connection string–primary key
connection_string = "Endpoint=sb://xxxxx.servicebus.windows.net/;SharedAccessKeyName=xxxxx;SharedAccessKey=REDACTED;EntityPath=xxxx"

async def send_events():
    # Create a producer client to send messages to the event hub.
    # Specify a connection string to event hubs namespace and the event hub name.
    producer = EventHubProducerClient.from_connection_string(connection_string)
    async with producer:
        batch = await producer.create_batch()

        orders = [
            {"OrderID": "O1", "Quantity": 10, "UnitPrice": 9.99, "DiscountCategory": "Tier 1"},
            {"OrderID": "O2", "Quantity": 15, "UnitPrice": 10.99, "DiscountCategory": "Tier 2"},
            {"OrderID": "O3", "Quantity": 20, "UnitPrice": 11.99, "DiscountCategory": "Tier 3"},
            {"OrderID": "O4", "Quantity": 25, "UnitPrice": 12.99, "DiscountCategory": "Tier 1"},
            {"OrderID": "O5", "Quantity": 30, "UnitPrice": 13.99, "DiscountCategory": "Tier 2"}
        ]

        for order in orders:
            event_data = EventData(json.dumps(order))
            try:
                batch.add(event_data)
            except Exception:
                await producer.send_batch(batch)
                batch = await producer.create_batch()
                batch.add(event_data)

        if batch:
            await producer.send_batch(batch)

    print("Batch of events sent")

asyncio.run(send_events())
