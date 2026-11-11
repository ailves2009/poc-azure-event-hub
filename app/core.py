"""Pure logic, no Azure SDK: event shape, consumer lag and health signals.

Kept separate so it is unit-tested offline and reused by producer, consumer and health.
"""

from __future__ import annotations

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass

# Event Hubs Standard limits per throughput unit (ingress).
TU_EVENTS_PER_SEC = 1000
TU_BYTES_PER_SEC = 1_000_000


def build_orders(count: int, customers: int, seed: int | None = None) -> list[dict]:
    """Generate demo orders. customer_id is the partition key, so all orders of one
    customer land in one partition and are read in the order they were sent."""
    rng = random.Random(seed)
    orders = []
    for i in range(count):
        orders.append(
            {
                "message_id": str(uuid.UUID(int=rng.getrandbits(128))),  # idempotency key
                "customer_id": f"C{rng.randrange(customers):04d}",
                "order_id": f"O{i:06d}",
                "quantity": rng.randint(1, 50),
                "unit_price": round(rng.uniform(1, 100), 2),
            }
        )
    return orders


def group_by_key(orders: list[dict], key: str = "customer_id") -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for order in orders:
        groups[order[key]].append(order)
    return dict(groups)


@dataclass(frozen=True)
class PartitionLag:
    partition_id: str
    last_enqueued: int  # sequence number of the newest event, -1 if the partition is empty
    checkpoint: int | None  # sequence number of the last processed event, None = never checkpointed
    lag: int


def compute_lag(last_enqueued: dict[str, int], checkpoints: dict[str, int]) -> list[PartitionLag]:
    """Events written but not yet processed, per partition.

    Sequence numbers start at 0 per partition. Without a checkpoint, the consumer has
    processed nothing, so the lag is every event still in the partition."""
    result = []
    for pid in sorted(last_enqueued, key=lambda p: int(p) if p.isdigit() else p):
        last = last_enqueued[pid]
        cp = checkpoints.get(pid)
        lag = (last + 1) if cp is None else max(last - cp, 0)
        result.append(PartitionLag(pid, last, cp, max(lag, 0)))
    return result


def signals(lags: list[PartitionLag], metrics: dict[str, float], throughput_units: int, window_sec: int) -> dict:
    """Deterministic health verdicts. The agent explains them; it does not compute them."""
    total_lag = sum(p.lag for p in lags)
    max_lag = max((p.lag for p in lags), default=0)
    mean_lag = total_lag / len(lags) if lags else 0

    incoming_per_sec = metrics.get("IncomingMessages", 0) / window_sec if window_sec else 0
    capacity_per_sec = throughput_units * TU_EVENTS_PER_SEC
    utilisation = incoming_per_sec / capacity_per_sec if capacity_per_sec else 0

    return {
        "consumer_lag_total": total_lag,
        "consumer_behind": total_lag > 0,
        "hot_partition": bool(lags) and mean_lag > 0 and max_lag > 2 * mean_lag,
        "throttled": metrics.get("ThrottledRequests", 0) > 0,
        "server_errors": metrics.get("ServerErrors", 0) > 0,
        "user_errors": metrics.get("UserErrors", 0) > 0,
        "ingress_utilisation": round(utilisation, 4),
        "near_capacity": utilisation >= 0.8,
    }


KAFKA_PORT = 9093  # Kafka endpoint of an Event Hubs namespace (Standard and higher)


def kafka_settings(fqdn: str, group_id: str) -> dict:
    """librdkafka settings for the Event Hubs Kafka endpoint with Entra ID (OAUTHBEARER).

    The event hub is the topic, the namespace is the cluster. No SASL password and no
    connection string: the token comes from the same identity and RBAC role as the SDK consumer."""
    return {
        "bootstrap.servers": f"{fqdn}:{KAFKA_PORT}",
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "OAUTHBEARER",
        "group.id": group_id,
        "auto.offset.reset": "earliest",  # a new group reads the whole retention window
        "enable.auto.commit": True,  # offsets live in the service, not in Blob
        "client.id": "poc-azure-event-hub-kafka",
    }
