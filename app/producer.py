"""Send demo orders to the event hub.

- Entra ID auth (no connection strings).
- Partition key = customer_id: per-customer ordering without pinning partitions.
- Batched sends: one call per full batch, which is what keeps a single TU unthrottled.
- message_id property: lets consumers de-duplicate (Event Hubs is at-least-once).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient
from azure.identity.aio import DefaultAzureCredential

import config
from core import build_orders, group_by_key


async def send(count: int, customers: int, seed: int | None) -> None:
    settings = config.load()
    orders = build_orders(count, customers, seed)
    started = time.monotonic()
    calls = 0

    async with DefaultAzureCredential() as credential:
        producer = EventHubProducerClient(
            fully_qualified_namespace=settings.fqdn,
            eventhub_name=settings.eventhub,
            credential=credential,
        )
        async with producer:
            for key, group in group_by_key(orders).items():
                batch = await producer.create_batch(partition_key=key)
                for order in group:
                    event = EventData(json.dumps(order))
                    event.content_type = "application/json"
                    event.properties = {"message_id": order["message_id"]}
                    try:
                        batch.add(event)
                    except ValueError:  # batch is full: ship it and start a new one
                        await producer.send_batch(batch)
                        calls += 1
                        batch = await producer.create_batch(partition_key=key)
                        batch.add(event)
                await producer.send_batch(batch)
                calls += 1

    elapsed = time.monotonic() - started
    print(f"sent {count} events for {customers} customers in {calls} send calls, {elapsed:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--customers", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None, help="reproducible orders")
    args = parser.parse_args()
    asyncio.run(send(args.count, args.customers, args.seed))


if __name__ == "__main__":
    main()
