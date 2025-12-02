import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from ...domain.flow.entities import Flow, FlowExecution, FlowContext, FlowStatus, StepType

logger = logging.getLogger(__name__)

class FlowEngine:
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.agent_dispatcher: Optional[Callable] = None

    def register_handler(self, name: str, handler: Callable):
        self.handlers[name] = handler

    def set_agent_dispatcher(self, dispatcher: Callable):
        self.agent_dispatcher = dispatcher

    async def execute_flow(self, flow: Flow, initial_data: Dict[str, Any] = None) -> FlowExecution:
        execution = FlowExecution(
            id=f"exec-{flow.id}",
            flow_id=flow.id,
            status=FlowStatus.RUNNING,
            current_step=flow.start_step,
            context=FlowContext(flow_id=flow.id, data=initial_data or {})
        )

        try:
            while execution.current_step:
                step_name = execution.current_step
                step = flow.steps.get(step_name)

                if not step:
                    raise ValueError(f"Step {step_name} not found in flow {flow.name}")

                logger.info(f"Executing step: {step_name} ({step.step_type})")

                result = None
                next_step_override = None

                if step.step_type == StepType.ACTION:
                    handler = self.handlers.get(step.handler)
                    if not handler:
                        raise ValueError(f"Handler {step.handler} not found")
                    result = await handler(execution.context, step.config)

                elif step.step_type == StepType.DECISION:
                    handler = self.handlers.get(step.handler)
                    if not handler:
                        raise ValueError(f"Handler {step.handler} not found")
                    next_step_override = await handler(execution.context, step.config)

                elif step.step_type == StepType.AGENT:
                    if not self.agent_dispatcher:
                        raise ValueError("Agent dispatcher not configured")
                    result = await self.agent_dispatcher(step.handler, execution.context, step.config)

                # Update history
                execution.context.history.append({
                    "step": step_name,
                    "result": result,
                    "timestamp": datetime.now()
                })

                # Determine next step
                if next_step_override:
                    execution.current_step = next_step_override
                else:
                    execution.current_step = step.next_step

            execution.status = FlowStatus.COMPLETED

        except Exception as e:
            logger.error(f"Flow failed: {e}")
            execution.status = FlowStatus.FAILED
            execution.error = str(e)

        execution.end_time = datetime.now()
        return execution
