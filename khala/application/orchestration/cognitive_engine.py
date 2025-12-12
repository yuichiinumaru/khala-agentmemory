"""Cognitive Cycle Engine.

Harvested from `drive-flow` and adapted for Khala.
Implements an event-driven DAG engine for agent reasoning loops, persisted via SurrealDB.
"""

import asyncio
import hashlib
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple, TypedDict, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from copy import copy
from enum import Enum

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.domain.audit.entities import AuditLog

logger = logging.getLogger(__name__)

# --- Types (Ported from drive-flow/types.py) ---

class ReturnBehavior(Enum):
    DISPATCH = "dispatch"
    GOTO = "goto"
    ABORT = "abort"
    INPUT = "input"

class TaskStatus(Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"

GroupEventReturns = Dict[str, Any]

@dataclass
class EventGroupInput:
    group_name: str
    results: GroupEventReturns
    behavior: ReturnBehavior = ReturnBehavior.DISPATCH

@dataclass
class EventInput(EventGroupInput):
    task_id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest())

@dataclass
class _SpecialEventReturn:
    behavior: ReturnBehavior
    returns: Any

# (group_event_results, global ctx) -> result
EventFunction = Callable[
    [Optional[EventInput], Optional[Any]], Awaitable[Union[Any, _SpecialEventReturn]]
]

@dataclass
class EventGroup:
    name: str
    events_hash: str
    events: Dict[str, "BaseEvent"]
    retrigger_type: Literal["all", "any"] = "all"

    def hash(self) -> str:
        return self.events_hash

def function_or_method_to_string(func):
    if hasattr(func, "__name__"):
        return func.__name__
    return str(func)

def string_to_md5_hash(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

class BaseEvent:
    parent_groups: Dict[str, EventGroup]
    func_inst: EventFunction
    id: str
    repr_name: str
    meta: Dict[str, Any]

    def __init__(
        self,
        func_inst: EventFunction,
        parent_groups: Optional[Dict[str, EventGroup]] = None,
    ):
        self.parent_groups = parent_groups or {}
        self.func_inst = func_inst
        self.id = string_to_md5_hash(function_or_method_to_string(self.func_inst))
        self.repr_name = function_or_method_to_string(self.func_inst)
        self.meta = {"func_name": self.repr_name}

    async def solo_run(
        self, event_input: EventInput, global_ctx: Any = None
    ) -> Any:
        return await self.func_inst(event_input, global_ctx)

class InvokeInterCache(TypedDict):
    result: Any
    already_sent_to_event_group: Set[str]


# --- Broker (SurrealDB Implementation) ---

class SurrealDBEventBroker:
    """Broker that logs event flow to SurrealDB via AuditRepository."""

    def __init__(self, client: SurrealDBClient, audit_repo: AuditRepository):
        self.client = client
        self.audit_repo = audit_repo

    async def log_event_start(self, event: BaseEvent, input_data: EventInput):
        """Log event start to audit trail."""
        try:
            log_entry = AuditLog(
                user_id="system", # or derived from ctx
                action="COGNITIVE_EVENT_START",
                target_id=event.id,
                target_type="event",
                details={
                    "event_name": event.repr_name,
                    "task_id": input_data.task_id,
                    "group_name": input_data.group_name
                },
                timestamp=datetime.now(timezone.utc)
            )
            await self.audit_repo.log(log_entry)
        except Exception as e:
            logger.warning(f"Failed to log event start: {e}")

    async def log_event_end(self, event: BaseEvent, result: Any):
        """Log event completion."""
        try:
            # Avoid logging massive results
            result_preview = str(result)[:200]
            log_entry = AuditLog(
                user_id="system",
                action="COGNITIVE_EVENT_END",
                target_id=event.id,
                target_type="event",
                details={
                    "event_name": event.repr_name,
                    "result_preview": result_preview
                },
                timestamp=datetime.now(timezone.utc)
            )
            await self.audit_repo.log(log_entry)
        except Exception as e:
            logger.warning(f"Failed to log event end: {e}")


# --- Engine (Ported Logic) ---

class CognitiveEngine:
    """Event-Driven DAG Engine for Agent Reasoning."""

    def __init__(
        self,
        name: str = "default",
        client: Optional[SurrealDBClient] = None,
        audit_repo: Optional[AuditRepository] = None
    ):
        self.name = name
        self.client = client
        self.audit_repo = audit_repo

        # Setup Broker
        if client and audit_repo:
            self.broker = SurrealDBEventBroker(client, audit_repo)
        else:
            self.broker = None # Or a dummy broker

        self.__event_maps: Dict[str, BaseEvent] = {}
        self.__max_group_size = 0

    def reset(self):
        self.__event_maps = {}

    def get_event_from_id(self, event_id: str) -> Optional[BaseEvent]:
        return self.__event_maps.get(event_id)

    def make_event(self, func: Union[EventFunction, BaseEvent]) -> BaseEvent:
        if isinstance(func, BaseEvent):
            self.__event_maps[func.id] = func
            return func

        if not inspect.iscoroutinefunction(func):
             # Wrap sync function if needed, or raise error.
             # drive-flow asserts iscoroutinefunction. We'll enforce it too.
             raise ValueError("Event function must be async")

        event = BaseEvent(func)
        self.__event_maps[event.id] = event
        return event

    def listen_group(
        self,
        group_markers: List[BaseEvent],
        group_name: Optional[str] = None,
        retrigger_type: Literal["all", "any"] = "all",
    ) -> Callable[[EventFunction], BaseEvent]:

        group_markers_in_dict = {event.id: event for event in group_markers}

        def decorator(func: Union[EventFunction, BaseEvent]) -> BaseEvent:
            if not isinstance(func, BaseEvent):
                func = self.make_event(func)

            this_group_name = group_name or f"{len(func.parent_groups)}"
            this_group_hash = string_to_md5_hash(":".join(sorted(group_markers_in_dict.keys())))

            new_group = EventGroup(
                name=this_group_name,
                events_hash=this_group_hash,
                events=group_markers_in_dict,
                retrigger_type=retrigger_type,
            )

            self.__max_group_size = max(
                self.__max_group_size, len(group_markers_in_dict)
            )

            if new_group.hash() in func.parent_groups:
                return func

            func.parent_groups[new_group.hash()] = new_group
            return func

        return decorator

    async def invoke_event(
        self,
        event: BaseEvent,
        event_input: Optional[EventInput] = None,
        global_ctx: Any = None,
        max_async_events: Optional[int] = None,
    ) -> Dict[str, InvokeInterCache]:

        this_run_ctx: Dict[str, InvokeInterCache] = {}
        queue: List[Tuple[str, EventInput]] = [(event.id, event_input)]

        async def run_event_wrapper(current_event_id: str, current_event_input: Any):
            current_event = self.get_event_from_id(current_event_id)
            if not current_event:
                raise ValueError(f"Event {current_event_id} not found")

            # Audit Log Start
            if self.broker:
                await self.broker.log_event_start(current_event, current_event_input)

            try:
                result = await current_event.solo_run(current_event_input, global_ctx)

                # Audit Log End
                if self.broker:
                    await self.broker.log_event_end(current_event, result)

            except Exception as e:
                logger.error(f"Error running event {current_event.repr_name}: {e}")
                raise e

            this_run_ctx[current_event.id] = {
                "result": result,
                "already_sent_to_event_group": set(),
            }

            if isinstance(result, _SpecialEventReturn):
                if result.behavior == ReturnBehavior.GOTO:
                    # GOTO Logic (from drive-flow)
                    group_markers, any_return = result.returns
                    for group_marker in group_markers:
                        # Logic to construct GOTO input
                        # simplified for this implementation
                        pass
                elif result.behavior == ReturnBehavior.ABORT:
                    return
            else:
                # Dispatch to children
                self._dispatch_to_children(current_event, this_run_ctx, queue)

        tasks = set()
        try:
            while len(queue) or len(tasks):
                # Simple throttling/batching
                this_batch_events = (
                    queue[:max_async_events] if max_async_events else queue
                )
                queue = queue[max_async_events:] if max_async_events else []

                new_tasks = {
                    asyncio.create_task(run_event_wrapper(*run_event_input))
                    for run_event_input in this_batch_events
                }
                tasks.update(new_tasks)

                if not tasks:
                    break

                done, tasks = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    await task # Raise exceptions
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        return this_run_ctx

    def _dispatch_to_children(self, current_event, this_run_ctx, queue):
        """Dispatch logic for downstream events."""
        for cand_event in self.__event_maps.values():
            for group_hash, group in cand_event.parent_groups.items():

                if current_event.id not in group.events:
                    continue

                # Check if all dependencies in group are met
                if not all(evt_id in this_run_ctx for evt_id in group.events):
                    continue

                event_group_id = f"{cand_event.id}:{group_hash}"

                # Check retrigger logic
                # (Simple 'all' logic: if any parent has already triggered this group for this event, skip)
                # Note: drive-flow logic is a bit complex here.
                # We check if *all* parents have marked this group as sent? No.
                # drive-flow:
                # if any([event_group_id in ctx[pid]["already_sent..."] for pid in group]) and retrigger=="all": skip

                already_triggered = False
                for pid in group.events:
                     if event_group_id in this_run_ctx[pid]["already_sent_to_event_group"]:
                         already_triggered = True
                         break

                if already_triggered and group.retrigger_type == "all":
                    continue

                # Prepare input
                group_results = {
                    eid: this_run_ctx[eid]["result"] for eid in group.events
                }

                # Mark as sent
                for pid in group.events:
                    this_run_ctx[pid]["already_sent_to_event_group"].add(event_group_id)

                build_input = EventInput(
                    group_name=group.name,
                    results=group_results
                )
                queue.append((cand_event.id, build_input))
