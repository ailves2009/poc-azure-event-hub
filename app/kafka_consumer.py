"""Read the same event hub with a plain Kafka client: no Azure SDK in the data path.

The point of the POC in one script: an unchanged Kafka client (librdkafka) talks to
Event Hubs over the Kafka protocol, authenticated with Entra ID (OAUTHBEARER), not a password.
- The event hub `orders` is the Kafka topic; the producer's partition key is the Kafka message key.
- Kafka consumer group offsets are stored by the service: no checkpoint store to run.
- It is an independent reader: its group does not affect `consumer.py` and its Blob checkpoints.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter

from azure.identity import DefaultAzureCredential
from confluent_kafka import Consumer

import config
from core import kafka_settings


def consume(duration: int, group_id: str) -> None:
    settings = config.load()
    credential = DefaultAzureCredential()
    scope = f"https://{settings.fqdn}/.default"

    def oauth_cb(_config: str) -> tuple[str, float]:
        token = credential.get_token(scope)  # refreshed by librdkafka before it expires
        return token.token, token.expires_on

    consumer = Consumer({**kafka_settings(settings.fqdn, group_id), "oauth_cb": oauth_cb})
    consumer.subscribe([settings.eventhub])
    per_partition: Counter[int] = Counter()
    deadline = time.monotonic() + duration
    try:
        while time.monotonic() < deadline:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"kafka error: {msg.error()}")
                continue
            per_partition[msg.partition()] += 1
            if per_partition[msg.partition()] <= 3:  # show a few, not all
                order = json.loads(msg.value())
                key = msg.key().decode() if msg.key() else None
                print(f"p{msg.partition()} offset={msg.offset()} key={key} {order['order_id']}")
    finally:
        consumer.close()  # commits the final offsets and leaves the group cleanly
        credential.close()

    total = sum(per_partition.values())
    summary = ", ".join(f"p{p}={n}" for p, n in sorted(per_partition.items()))
    print(f"kafka group {group_id}: {total} events in {duration}s ({summary or 'nothing new'})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--duration", type=int, default=30, help="seconds to listen")
    parser.add_argument("--group", default="orders-kafka", help="Kafka consumer group (created on first use)")
    args = parser.parse_args()
    consume(args.duration, args.group)


if __name__ == "__main__":
    main()
