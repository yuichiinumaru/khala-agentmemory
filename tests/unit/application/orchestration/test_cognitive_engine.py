import pytest
import asyncio
from unittest.mock import AsyncMock
from khala.application.orchestration.cognitive_engine import CognitiveEngine, EventInput

@pytest.mark.asyncio
async def test_simple_chain():
    engine = CognitiveEngine()

    @engine.make_event
    async def step1(event, ctx):
        return 1

    @engine.listen_group([step1])
    async def step2(event: EventInput, ctx):
        # Access result from previous step
        prev = event.results[step1.id]
        return prev + 1

    # Invoke
    results = await engine.invoke_event(step1, EventInput("start", {}))

    # Check execution
    assert step1.id in results
    assert step2.id in results
    assert results[step1.id]["result"] == 1
    assert results[step2.id]["result"] == 2

@pytest.mark.asyncio
async def test_branching():
    engine = CognitiveEngine()

    @engine.make_event
    async def root(event, ctx):
        return "root"

    @engine.listen_group([root])
    async def branch_a(event, ctx):
        return "A"

    @engine.listen_group([root])
    async def branch_b(event, ctx):
        return "B"

    @engine.listen_group([branch_a, branch_b])
    async def merge(event, ctx):
        # Results from both parents
        res_a = event.results[branch_a.id]
        res_b = event.results[branch_b.id]
        return f"{res_a}-{res_b}"

    results = await engine.invoke_event(root, EventInput("start", {}))

    assert merge.id in results
    assert results[merge.id]["result"] == "A-B"

@pytest.mark.asyncio
async def test_context_passing():
    engine = CognitiveEngine()

    @engine.make_event
    async def step1(event, ctx):
        return ctx["val"]

    results = await engine.invoke_event(step1, EventInput("start", {}), global_ctx={"val": 42})

    assert results[step1.id]["result"] == 42
