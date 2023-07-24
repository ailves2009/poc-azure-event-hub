from azure.eventhub.aio import EventHubConsumerClient
import asyncio
import json

# add value from /Event Hubs Instance/Shared access policies/[your polycy name]/Connection string–primary key
connection_string = "Endpoint=sb://xxxxx.servicebus.windows.net/;SharedAccessKeyName=xxxxx;SharedAccessKey=REDACTED;EntityPath=xxxx"

async def on_event(partition_context, event):
    print(f"Partition ID: {partition_context.partition_id}")
    print(f"Data Offset: {event.offset}")
    print(f"Sequence Number: {event.sequence_number}")
    print(f"Partition Key: {event.partition_key}")
    body = b"".join(event.body)
    print(f"Event Body: {body.decode('utf-8')}")
    await partition_context.update_checkpoint(event)
    print(f" ")

async def receive_events():
    client = EventHubConsumerClient.from_connection_string(connection_string, consumer_group="$Default")
    async with client:
        await client.receive(on_event=on_event, starting_position="-1")

asyncio.run(receive_events())
