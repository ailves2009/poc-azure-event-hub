"""Health facts as JSON: consumer lag per partition, namespace metrics, verdicts.

Deterministic and read-only. This is the only input the triage agent
(.claude/skills/eventhub-triage) works from: the script decides, the agent explains.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from dataclasses import asdict

from azure.eventhub.aio import EventHubConsumerClient
from azure.eventhub.extensions.checkpointstoreblobaio import BlobCheckpointStore
from azure.identity.aio import DefaultAzureCredential

import config
from core import compute_lag, signals

METRICS = ["IncomingMessages", "OutgoingMessages", "ThrottledRequests", "ServerErrors", "UserErrors"]


async def partition_state(settings: config.Settings) -> tuple[dict[str, int], dict[str, int]]:
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
        )
        async with client, store:
            last_enqueued = {}
            for pid in await client.get_partition_ids():
                props = await client.get_partition_properties(pid)
                last_enqueued[pid] = -1 if props["is_empty"] else props["last_enqueued_sequence_number"]
            checkpoints = {
                cp["partition_id"]: cp["sequence_number"]
                for cp in await store.list_checkpoints(settings.fqdn, settings.eventhub, settings.consumer_group)
            }
    return last_enqueued, checkpoints


def namespace_metrics(namespace_id: str, window: str) -> dict[str, float]:
    """Totals over the window via the Azure CLI (already logged in, no extra SDK)."""
    out = subprocess.run(
        [
            "az",
            "monitor",
            "metrics",
            "list",
            "--resource",
            namespace_id,
            "--metrics",
            *METRICS,
            "--aggregation",
            "Total",
            "--interval",
            "PT5M",
            "--offset",
            window,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    totals: dict[str, float] = {}
    for metric in json.loads(out.stdout)["value"]:
        name = metric["name"]["value"]
        totals[name] = sum(point.get("total") or 0 for series in metric["timeseries"] for point in series["data"])
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window-minutes", type=int, default=60)
    args = parser.parse_args()
    settings = config.load()

    last_enqueued, checkpoints = asyncio.run(partition_state(settings))
    lags = compute_lag(last_enqueued, checkpoints)

    metrics_error = None
    try:
        metrics = namespace_metrics(settings.namespace_id, f"{args.window_minutes}m")
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        metrics, metrics_error = {}, str(exc)[:300]

    facts = {
        "eventhub": settings.eventhub,
        "consumer_group": settings.consumer_group,
        "throughput_units": settings.throughput_units,
        "partitions": [asdict(p) for p in lags],
        "metrics_window_minutes": args.window_minutes,
        "metrics": metrics,
        "metrics_error": metrics_error,
        "signals": signals(lags, metrics, settings.throughput_units, args.window_minutes * 60),
    }
    json.dump(facts, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
