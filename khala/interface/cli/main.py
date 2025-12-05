"""Primary command-line entry point for KHALA."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, TypeVar

import click
from pydantic import ValidationError, SecretStr
from rich.console import Console
from rich.table import Table

from ...application.orchestration.gemini_subagent_system import create_subagent_system
from ...domain.memory.entities import Memory
from ...domain.memory.services import MemoryService
from ...domain.memory.value_objects import ImportanceScore, MemoryTier
from ...infrastructure.cache.cache_manager import create_cache_manager
from ...infrastructure.surrealdb.client import SurrealDBClient, SurrealConfig

console = Console()
T = TypeVar("T")


def _format_dict_table(title: str, data: dict[str, Any]) -> Table:
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for key, value in data.items():
        if isinstance(value, float):
            value_repr = f"{value:.2f}"
        elif isinstance(value, datetime):
            value_repr = value.isoformat()
        else:
            value_repr = str(value)
        table.add_row(key.replace("_", " ").title(), value_repr)
    return table


def _load_content(content: str | None, content_file: Path | None) -> str:
    if content:
        return content.strip()
    if content_file:
        return content_file.read_text(encoding="utf-8").strip()
    raise click.UsageError("Provide --content or --content-file.")


def _ensure_importance(value: float) -> ImportanceScore:
    try:
        return ImportanceScore(value)
    except (TypeError, ValueError) as exc:
        raise click.BadParameter(str(exc)) from exc


def _run_async(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


def _create_memory(
    *,
    user_id: str,
    content: str,
    tier: MemoryTier,
    importance: ImportanceScore,
    access_count: int,
    age_hours: float,
) -> Memory:
    if access_count < 0:
        raise click.BadParameter("--access-count must be non-negative")
    if age_hours < 0:
        raise click.BadParameter("--age-hours must be non-negative")

    created_at = datetime.now(UTC) - timedelta(hours=age_hours)
    memory = Memory(
        user_id=user_id,
        content=content,
        tier=tier,
        importance=importance,
        access_count=access_count,
        created_at=created_at,
        updated_at=created_at,
        accessed_at=created_at,
    )
    return memory


@click.group()
@click.option("--max-agents", default=4, show_default=True, type=click.IntRange(1, 32))
@click.pass_context
def cli(ctx: click.Context, max_agents: int) -> None:
    """KHALA command-line utilities."""

    ctx.ensure_object(dict)
    ctx.obj["max_agents"] = max_agents


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show current subagent system metrics."""

    system = create_subagent_system(ctx.obj["max_agents"])
    metrics = system.get_performance_metrics()
    console.print(_format_dict_table("KHALA Subagent Metrics", metrics))


@cli.command("simulate-promotion")
@click.option("--user-id", default="cli_user", show_default=True)
@click.option("--content", type=str, help="Memory content to evaluate.")
@click.option(
    "--content-file",
    type=click.Path(path_type=Path, dir_okay=False, exists=True, readable=True),
    help="Load memory content from a file.",
)
@click.option(
    "--tier",
    type=click.Choice([tier.value for tier in MemoryTier], case_sensitive=False),
    default=MemoryTier.WORKING.value,
    show_default=True,
)
@click.option(
    "--importance",
    type=float,
    default=0.7,
    show_default=True,
    help="Importance score in the range [0.0, 1.0].",
)
@click.option(
    "--access-count",
    type=int,
    default=0,
    show_default=True,
    help="Historical access count for the memory.",
)
@click.option(
    "--age-hours",
    type=float,
    default=0.0,
    show_default=True,
    help="Simulated memory age in hours.",
)
def simulate_promotion(
    user_id: str,
    content: str | None,
    content_file: Path | None,
    tier: str,
    importance: float,
    access_count: int,
    age_hours: float,
) -> None:
    """Estimate promotion readiness for a memory sample."""

    memory_content = _load_content(content, content_file)
    memory = _create_memory(
        user_id=user_id,
        content=memory_content,
        tier=MemoryTier(tier.lower()),
        importance=_ensure_importance(importance),
        access_count=access_count,
        age_hours=age_hours,
    )

    service = MemoryService()
    promotion_score = service.calculate_promotion_score(memory)
    should_promote = False
    try:
        should_promote = memory.should_promote_to_next_tier()
    except ValueError:
        should_promote = False

    table = Table(title="Memory Promotion Analysis", show_header=False)
    table.add_row("Memory ID", memory.id)
    table.add_row("Current Tier", memory.tier.value)
    next_tier = memory.tier.next_tier()
    table.add_row("Next Tier", next_tier.value if next_tier else "n/a")
    table.add_row("Importance", f"{memory.importance.value:.2f}")
    table.add_row("Access Count", str(memory.access_count))
    table.add_row("Age (hours)", f"{memory.get_age_hours():.2f}") # Use public method
    table.add_row("Promotion Score", f"{promotion_score:.2f}")
    table.add_row("Promotion Eligible", "Yes" if should_promote else "No")
    console.print(table)


@cli.command("surreal-health")
@click.option("--url", default="ws://localhost:8000/rpc", show_default=True, envvar="SURREAL_URL")
@click.option("--namespace", default="khala", show_default=True, envvar="SURREAL_NS")
@click.option("--database", default="memories", show_default=True, envvar="SURREAL_DB")
@click.option("--username", required=True, envvar="SURREAL_USER", help="DB Username")
@click.option("--password", required=True, envvar="SURREAL_PASS", help="DB Password")
def surreal_health(
    url: str,
    namespace: str,
    database: str,
    username: str,
    password: str,
) -> None:
    """Check SurrealDB connectivity and query responsiveness."""

    try:
        result = _run_async(
            _surreal_health_check(url, namespace, database, username, password)
        )
    except Exception as exc: # Catch generic to display in CLI
        raise click.ClickException(str(exc)) from exc

    table = Table(title="SurrealDB Health", show_header=False)
    table.add_row("Status", "OK")
    table.add_row("URL", result["url"])
    table.add_row("Namespace", result["namespace"])
    table.add_row("Database", result["database"])
    table.add_row("Connection (ms)", f"{result['connect_ms']:.2f}")
    table.add_row("Query (ms)", f"{result['query_ms']:.2f}")
    console.print(table)


@cli.command("cache-metrics")
@click.option("--redis-url", default="redis://localhost:6379/2", show_default=True)
def cache_metrics(redis_url: str) -> None:
    """Show multi-level cache connectivity and hit rates."""

    try:
        metrics = _run_async(_collect_cache_metrics(redis_url))
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    hit_table = Table(title="Cache Hit Rates")
    hit_table.add_column("Level", style="cyan")
    hit_table.add_column("Hit Rate", style="green")
    hit_table.add_row("L1", f"{metrics['hit_rates']['l1']:.2%}")
    hit_table.add_row("L2", f"{metrics['hit_rates']['l2']:.2%}")
    hit_table.add_row("L3", f"{metrics['hit_rates']['l3']:.2%}")
    hit_table.add_row("Overall", f"{metrics['hit_rates']['overall']:.2%}")

    perf_table = Table(title="Cache Performance", show_header=False)
    perf_table.add_row(
        "Total Responses", str(metrics["performance"]["total_responses"])
    )
    perf_table.add_row(
        "Avg Response (ms)", f"{metrics['performance']['avg_response_time_ms']:.2f}"
    )

    level_table = Table(title="Cache Levels")
    level_table.add_column("Level", style="cyan")
    level_table.add_column("Detail", style="green")

    l1_stats = metrics["levels"]["l1"]
    level_table.add_row(
        "L1",
        (
            f"items={l1_stats['total_items']} size={l1_stats['total_size_bytes']}B "
            f"evictions={l1_stats['evictions']}"
        ),
    )
    level_table.add_row(
        "L2",
        "connected" if metrics["levels"]["l2"]["connected"] else "not connected",
    )
    level_table.add_row(
        "L3",
        "connected" if metrics["levels"]["l3"]["connected"] else "not connected",
    )

    console.print(hit_table)
    console.print(perf_table)
    console.print(level_table)


async def _surreal_health_check(
    url: str,
    namespace: str,
    database: str,
    username: str,
    password: str,
) -> dict[str, Any]:

    # Use SurrealConfig for validation and safety
    try:
        config = SurrealConfig(
            url=url,
            namespace=namespace,
            database=database,
            username=username,
            password=SecretStr(password)
        )
    except ValidationError as e:
        raise ValueError(f"Invalid Configuration: {e}")

    client = SurrealDBClient(config)

    connect_start = perf_counter()
    try:
        await client.initialize()
        connect_ms = (perf_counter() - connect_start) * 1000
        query_start = perf_counter()
        async with client.get_connection() as connection:
            await connection.query("RETURN true;")
        query_ms = (perf_counter() - query_start) * 1000
    except Exception as exc:  # pragma: no cover - raised for CLI output
        raise RuntimeError(f"SurrealDB health check failed: {exc}") from exc
    finally:
        await client.close()

    return {
        "url": url,
        "namespace": namespace,
        "database": database,
        "connect_ms": connect_ms,
        "query_ms": query_ms,
    }


async def _collect_cache_metrics(redis_url: str) -> dict[str, Any]:
    manager = create_cache_manager(l2_redis_url=redis_url)
    try:
        await manager.start()
        return manager.get_metrics()
    except Exception as exc:  # pragma: no cover - raised for CLI output
        raise RuntimeError(f"Cache metrics collection failed: {exc}") from exc
    finally:
        await manager.stop()


if __name__ == "__main__":  # pragma: no cover
    cli()
