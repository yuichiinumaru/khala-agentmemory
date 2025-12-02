"""CLI contract tests for KHALA."""

import sys
import types
from contextlib import asynccontextmanager

from click.testing import CliRunner


class _DummyBaseSurreal:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def connect(self) -> None:
        return None

    async def signin(self, *_args, **_kwargs) -> None:
        return None

    async def use(self, **_kwargs) -> None:
        return None

    async def query(self, *_args, **_kwargs) -> list[dict[str, bool]]:
        return [{"result": True}]

    async def close(self) -> None:
        return None


_surreal_module = types.ModuleType("surrealdb")
_surreal_module.Surreal = _DummyBaseSurreal  # type: ignore[attr-defined]
_surreal_module.AsyncSurreal = _DummyBaseSurreal  # type: ignore[attr-defined]

_surreal_async_module = types.ModuleType("surrealdb.asyncio")
_surreal_async_module.Surreal = _DummyBaseSurreal  # type: ignore[attr-defined]
_surreal_async_module.AsyncSurreal = _DummyBaseSurreal  # type: ignore[attr-defined]

sys.modules.setdefault("surrealdb", _surreal_module)
sys.modules.setdefault("surrealdb.asyncio", _surreal_async_module)

_schema_module = types.ModuleType("khala.infrastructure.surrealdb.schema")


class _DummySchema:  # pragma: no cover - simple placeholder
    async def get_schema_info(self) -> dict[str, object]:
        return {}


_schema_module.DatabaseSchema = _DummySchema  # type: ignore[attr-defined]
sys.modules.setdefault("khala.infrastructure.surrealdb.schema", _schema_module)

from khala.interface.cli.main import cli  # noqa: E402


def test_status_command_outputs_metrics() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])

    assert result.exit_code == 0
    assert "KHALA Subagent Metrics" in result.output
    assert "Total Tasks" in result.output


def test_simulate_promotion_command_reports_analysis() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "simulate-promotion",
            "--content",
            "Test memory content for analysis",
            "--importance",
            "0.8",
            "--access-count",
            "3",
            "--age-hours",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "Memory Promotion Analysis" in result.output
    assert "Promotion Score" in result.output


def test_surreal_health_command(monkeypatch) -> None:
    class _DummyConnection:
        async def query(self, _statement: str) -> list[dict[str, bool]]:
            return [{"result": True}]

    class _DummySurrealClient:
        def __init__(self, **_kwargs) -> None:
            self.closed = False

        async def initialize(self) -> None:
            return None

        @asynccontextmanager
        async def get_connection(self):
            yield _DummyConnection()

        async def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("khala.interface.cli.main.SurrealDBClient", _DummySurrealClient)

    runner = CliRunner()
    result = runner.invoke(cli, ["surreal-health"])

    assert result.exit_code == 0
    assert "SurrealDB Health" in result.output
    assert "Status" in result.output


def test_cache_metrics_command(monkeypatch) -> None:
    class _DummyCacheManager:
        def __init__(self, *_, **__):
            self.started = False

        async def start(self) -> None:
            self.started = True

        async def stop(self) -> None:
            self.started = False

        def get_metrics(self) -> dict[str, object]:
            return {
                "hit_rates": {"l1": 0.5, "l2": 0.1, "l3": 0.0, "overall": 0.3},
                "levels": {
                    "l1": {
                        "total_items": 4,
                        "total_size_bytes": 512,
                        "max_memory_bytes": 104857600,
                        "evictions": 1,
                        "hit_rate": 0.5,
                        "ttl_seconds": 300,
                    },
                    "l2": {"connected": True},
                    "l3": {"connected": False},
                },
                "performance": {
                    "total_responses": 10,
                    "avg_response_time_ms": 12.5,
                },
            }

    def _fake_factory(*args, **kwargs):
        return _DummyCacheManager(*args, **kwargs)

    monkeypatch.setattr("khala.interface.cli.main.create_cache_manager", _fake_factory)

    runner = CliRunner()
    result = runner.invoke(cli, ["cache-metrics"])

    assert result.exit_code == 0
    assert "Cache Hit Rates" in result.output
    assert "Cache Levels" in result.output
