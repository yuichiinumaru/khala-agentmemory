import pytest
import asyncio
from datetime import datetime

from khala.domain.flow.entities import Flow, FlowStep, StepType, FlowStatus
from khala.application.flow.engine import FlowEngine
from khala.domain.agent.entities import AgentProfile, AgentRole
from khala.application.crew.orchestrator import CrewOrchestrator

# --- Flow Tests ---
async def action_step(context, config):
    context.data["result"] = "Action Completed"
    return "Action Done"

async def decision_step(context, config):
    if context.data.get("result") == "Action Completed":
        return "end_step"
    return "fail_step"

async def end_step_handler(context, config):
    return "Finished"

@pytest.mark.asyncio
async def test_flow_execution():
    engine = FlowEngine()
    engine.register_handler("action_handler", action_step)
    engine.register_handler("decision_handler", decision_step)
    engine.register_handler("end_handler", end_step_handler)

    flow = Flow(
        id="flow-1",
        name="Test Flow",
        start_step="step1",
        steps={
            "step1": FlowStep(name="step1", step_type=StepType.ACTION, handler="action_handler", next_step="step2"),
            "step2": FlowStep(name="step2", step_type=StepType.DECISION, handler="decision_handler"),
            "end_step": FlowStep(name="end_step", step_type=StepType.ACTION, handler="end_handler"),
        }
    )

    execution = await engine.execute_flow(flow, initial_data={"input": "start"})

    assert execution.status == FlowStatus.COMPLETED
    assert len(execution.context.history) == 3
    assert execution.context.history[0]['result'] == "Action Done"

# --- Crew Tests ---
@pytest.mark.asyncio
async def test_crew_delegation():
    orchestrator = CrewOrchestrator()

    # Create Agents
    manager = AgentProfile(id="agent-1", name="Manager Bob", role=AgentRole.MANAGER, capabilities=["planning", "management"])
    worker = AgentProfile(id="agent-2", name="Worker Alice", role=AgentRole.WORKER, capabilities=["analyst", "worker"])
    reviewer = AgentProfile(id="agent-3", name="Reviewer Charlie", role=AgentRole.WORKER, capabilities=["reviewer"])

    # Create Crew
    crew = orchestrator.create_crew(
        name="Alpha Team",
        mission="Solve complex problems",
        members=[manager, worker, reviewer]
    )

    assert crew.name == "Alpha Team"
    assert crew.get_leader().profile.name == "Manager Bob"

    # Delegate Task
    result = await orchestrator.delegate_task(
        crew_id=crew.id,
        task="Build a website",
        context={}
    )

    assert result["crew_id"] == crew.id
    assert len(result["results"]) == 3

    # Check assignments (based on updated logic)
    assignments = {r['task']: r['assignee'] for r in result["results"]}

    # "Analyze requirements for Build a website" -> required_role: analyst -> Alice
    # Note: assignments key is the full task description

    analyze_task = next((r for r in result["results"] if "Analyze" in r['task']), None)
    assert analyze_task is not None
    assert analyze_task['assignee'] == "Worker Alice"

    verify_task = next((r for r in result["results"] if "Verify" in r['task']), None)
    assert verify_task is not None
    assert verify_task['assignee'] == "Reviewer Charlie"
