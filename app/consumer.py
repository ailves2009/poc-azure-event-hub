"""Read orders with a durable checkpoint in Blob Storage.

- Checkpoints survive restarts: a new run continues where the last one stopped.
- Run two consumers at once and they split the partitions between them
  (load balancing through the same checkpoint store).
- At-least-once: an event can be seen twice after a crash between processing and
  checkpoint, so processing must be idempotent (message_id).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter

from azure.eventhub.aio import EventHubConsumerClient
from azure.eventhub.extensions.checkpointstoreblobaio import BlobCheckpointStore
from azure.identity.aio import DefaultAzureCredential

import config

CHECKPOINT_EVERY = 50  # trade-off: fewer storage writes vs. more re-delivery after a crash


async def consume(duration: int) -> None:
    settings = config.load()
    processed: Counter[str] = Counter()
    pending: dict[str, tuple] = {}  # partition -> (context, last event not yet checkpointed)

    async def checkpoint(pid: str) -> None:
        ctx, event = pending.pop(pid)
        await ctx.update_checkpoint(event)

    async def on_event(ctx, event) -> None:
        pid = ctx.partition_id
        order = json.loads(event.body_as_str())
        processed[pid] += 1
        if processed[pid] <= 3:  # show a few, not all
            print(f"p{pid} seq={event.sequence_number} {order['customer_id']} {order['order_id']}")
        pending[pid] = (ctx, event)
        if processed[pid] % CHECKPOINT_EVERY == 0:
            await checkpoint(pid)

    async def on_partition_initialize(ctx) -> None:
        print(f"claimed partition {ctx.partition_id}")

    async def on_partition_close(ctx, reason) -> None:
        print(f"released partition {ctx.partition_id}: {reason}")

    async def on_error(ctx, error) -> None:
        print(f"error on {ctx.partition_id if ctx else 'load balancer'}: {error!r}")

    async with DefaultAzureCredential() as credential:
        store = BlobCheckpointStore(
            blob_account_url=settings.checkpoint_account_url,
            container_name=settings.checkpoint_container,
            credential=credential,
        )
        client = EventHubConsumerClient(
            fully_qualified_namespace=settings.fqdn,
            eventhub_name=settings.eventhub,
            consumer_group=settings.consumer_group,
            credential=credential,
            checkpoint_store=store,
        )
        async with client:
            receiving = asyncio.create_task(
                client.receive(
                    on_event=on_event,
                    on_error=on_error,
                    on_partition_initialize=on_partition_initialize,
                    on_partition_close=on_partition_close,
                    starting_position="-1",  # only used when a partition has no checkpoint yet
                )
            )
            await asyncio.sleep(duration)
            for pid in list(pending):  # graceful stop: persist progress before leaving
                await checkpoint(pid)
            receiving.cancel()
            try:
                await receiving
            except asyncio.CancelledError:
                pass
        await store.close()

    total = sum(processed.values())
    per_partition = ", ".join(f"p{p}={n}" for p, n in sorted(processed.items()))
    print(f"processed {total} events in {duration}s ({per_partition or 'nothing new'})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--duration", type=int, default=30, help="seconds to listen")
    args = parser.parse_args()
    asyncio.run(consume(args.duration))


if __name__ == "__main__":
    main()
