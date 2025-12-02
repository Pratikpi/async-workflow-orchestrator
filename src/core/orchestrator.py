"""Workflow orchestrator with state machine using transitions library."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from transitions import Machine
from sqlalchemy.orm import Session

from src.db import Workflow, WorkflowTransition, WorkflowStatus
from src.db.dao.workflow_dao import WorkflowDAO
from src.db.dao.workflow_transition_dao import WorkflowTransitionDAO


logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates workflow execution using a state machine.
    Uses asyncio for coordination and event handling.
    Implements INIT → PREPARE → EXECUTE → VALIDATE → COMPLETE state flow.
    """
    
    # State machine states
    states = ['INIT', 'PREPARE', 'EXECUTE', 'VALIDATE', 'COMPLETE', 'FAILED', 'CANCELLED']
    
    # State to task type mapping
    STATE_TASKS = {
        'INIT': 'initialize',
        'PREPARE': 'prepare',
        'EXECUTE': 'execute',
        'VALIDATE': 'validate',
        'COMPLETE': 'complete'
    }
    
    def __init__(self, workflow_id: int, db: Session):
        """Initialize the orchestrator for a specific workflow."""
        self.workflow_id = workflow_id
        self.db = db
        self.workflow_dao = WorkflowDAO(db)
        self.transition_dao = WorkflowTransitionDAO(db)
        self.workflow = self._load_workflow()

        # Define transitions for the workflow lifecycle
        # INIT → PREPARE → EXECUTE → VALIDATE → COMPLETE
        self.transitions = [
            {'trigger': 'prepare', 'source': 'INIT', 'dest': 'PREPARE', 'before': '_on_state_enter', 'after': '_log_transition'},
            {'trigger': 'execute', 'source': 'PREPARE', 'dest': 'EXECUTE', 'before': '_on_state_enter', 'after': '_log_transition'},
            {'trigger': 'validate', 'source': 'EXECUTE', 'dest': 'VALIDATE', 'before': '_on_state_enter', 'after': '_log_transition'},
            {'trigger': 'complete', 'source': 'VALIDATE', 'dest': 'COMPLETE', 'before': '_on_complete', 'after': '_log_transition'},
            {'trigger': 'fail', 'source': ['INIT', 'PREPARE', 'EXECUTE', 'VALIDATE'], 'dest': 'FAILED', 'before': '_on_fail', 'after': '_log_transition'},
            {'trigger': 'cancel', 'source': ['INIT', 'PREPARE', 'EXECUTE', 'VALIDATE'], 'dest': 'CANCELLED', 'before': '_on_cancel', 'after': '_log_transition'},
            {'trigger': 'retry', 'source': 'FAILED', 'dest': 'INIT'}
        ]

        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=WorkflowOrchestrator.states,
            initial=self.workflow.status.value,
            transitions=self.transitions,
            auto_transitions=False,
            send_event=True,
        )
        
        self._event_queue = asyncio.Queue()
        self._running = False
        self._task_results = {}
    
    def _load_workflow(self) -> Workflow:
        """Load workflow from database."""
        workflow = self.workflow_dao.get_by_id(self.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {self.workflow_id} not found")
        return workflow
    
    def _log_transition(self, event):
        """Log state transitions to database."""
        transition = WorkflowTransition(
            workflow_id=self.workflow_id,
            from_state=event.transition.source,
            to_state=event.transition.dest,
            trigger=event.event.name,
            metadata={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
        self.transition_dao.create(transition)
        
        # Update workflow status and current_state
        self.workflow_dao.update(self.workflow_id, {
            "status": WorkflowStatus(event.transition.dest),
            "current_state": event.transition.dest,
            "updated_at": datetime.now(timezone.utc)
        })
        
        # Refresh local workflow object
        self.workflow = self.workflow_dao.get_by_id(self.workflow_id)
        
        logger.info(
            f"Workflow {self.workflow_id}: {event.transition.source} → "
            f"{event.transition.dest} (trigger: {event.event.name})"
        )
    
    def _on_state_enter(self, event):
        """Handle entering a new workflow state."""
        logger.info(f"Entering state {event.transition.dest} for workflow {self.workflow_id}")
        if self.workflow.started_at is None:
            self.workflow.started_at = datetime.now(timezone.utc)
            self.workflow_dao.update(self.workflow_id, {"started_at": self.workflow.started_at})
    
    def _on_complete(self, event):
        """Handle workflow completion."""
        completed_at = datetime.now(timezone.utc)
        self.workflow_dao.update(self.workflow_id, {"completed_at": completed_at})
        self.workflow.completed_at = completed_at
        logger.info(f"Completed workflow {self.workflow_id}")
    
    def _on_fail(self, event):
        """Handle workflow failure."""
        completed_at = datetime.now(timezone.utc)
        error_msg = str(event.kwargs.get('error', 'Unknown error'))
        
        self.workflow_dao.update(self.workflow_id, {
            "completed_at": completed_at,
            "error_message": error_msg
        })
        
        self.workflow.completed_at = completed_at
        self.workflow.error_message = error_msg
        logger.error(f"Failed workflow {self.workflow_id}: {error_msg}")
    
    def _on_cancel(self, event):
        """Handle workflow cancellation."""
        completed_at = datetime.now(timezone.utc)
        self.workflow_dao.update(self.workflow_id, {"completed_at": completed_at})
        self.workflow.completed_at = completed_at
        logger.info(f"Cancelled workflow {self.workflow_id}")
    
    def _on_retry(self, event):
        """Handle workflow retry."""
        self.workflow_dao.update(self.workflow_id, {
            "retries": self.workflow.retries + 1,
            "error_message": None,
            "completed_at": None,
            "started_at": None
        })
        # Refresh local state
        self.workflow = self.workflow_dao.get_by_id(self.workflow_id)
        logger.info(f"Retrying workflow {self.workflow_id} (attempt {self.workflow.retries})")
    
    async def emit_event(self, event_name: str, **kwargs):
        """Emit an event to the orchestrator."""
        await self._event_queue.put((event_name, kwargs))
    
    def _transition_to_next_state(self):
        """
        Transition to the next state in the workflow.
        This is a synchronous version for simple state progression.
        """
        next_trigger = self.get_next_trigger()
        if next_trigger:
            logger.info(f"Transitioning workflow {self.workflow_id} via trigger: {next_trigger}")
            trigger_method = getattr(self, next_trigger)
            trigger_method()
        else:
            logger.info(f"Workflow {self.workflow_id} in terminal state: {self.state}")
    
    async def execute_workflow(self, worker_manager):
        """
        Execute the entire workflow automatically.
        Alias for execute_automatic for backward compatibility.
        
        Args:
            worker_manager: WorkerManager instance for executing tasks
        """
        return await self.execute_automatic(worker_manager)
    
    async def process_events(self):
        """Process events from the queue."""
        self._running = True
        
        while self._running:
            try:
                # Wait for event with timeout
                event_name, kwargs = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                # Trigger state machine transition
                if hasattr(self, event_name):
                    trigger = getattr(self, event_name)
                    trigger(**kwargs)
                else:
                    logger.warning(f"Unknown event: {event_name}")
                
            except asyncio.TimeoutError:
                # No events, continue
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                await self.emit_event('fail', error=str(e))
    
    def get_next_trigger(self) -> Optional[str]:
        """
        Determine the next trigger based on current state.
        Returns the trigger name to advance to the next state.
        """
        for transition in self.transitions:
            if transition['source'] == self.state:
                return transition['trigger']
        return None
    
    async def advance_to_next_state(self):
        """Advance workflow to the next state after task completion."""
        next_trigger = self.get_next_trigger()
        if next_trigger:
            logger.info(f"Advancing workflow {self.workflow_id} via trigger: {next_trigger}")
            await self.emit_event(next_trigger)
        else:
            logger.info(f"Workflow {self.workflow_id} in terminal state: {self.state}")
    
    async def execute_automatic(self, worker_manager):
        """
        Execute the workflow automatically through all states.
        
        Args:
            worker_manager: WorkerManager instance for executing tasks
        """
        try:
            # Start event processor
            event_task = asyncio.create_task(self.process_events())
            
            # Progress through all workflow states
            workflow_sequence = ['INIT', 'PREPARE', 'EXECUTE', 'VALIDATE', 'COMPLETE']
            current_index = workflow_sequence.index(self.state)
            
            logger.info(f"Starting automatic execution from state {self.state}")
            
            # Execute each state in sequence
            for state in workflow_sequence[current_index:]:
                if state == 'COMPLETE':
                    # Trigger final completion
                    await self.advance_to_next_state()
                    break
                
                # Get task type for this state
                task_type = self.STATE_TASKS.get(state, 'default')
                
                logger.info(f"Executing {task_type} task for state {state}")
                
                # Submit task to worker manager
                task_config = {
                    'workflow_id': self.workflow_id,
                    'state': state,
                    'task_type': task_type
                }
                
                # Execute task in thread pool
                future = worker_manager.submit_workflow_task(
                    self.workflow_id, 
                    task_type, 
                    task_config,
                    self.db
                )
                
                # Wait for task completion
                result = await asyncio.get_event_loop().run_in_executor(None, future.result)
                
                if not result.get('success', False):
                    # Task failed
                    error = result.get('error', 'Task execution failed')
                    await self.emit_event('fail', error=error)
                    self._running = False
                    await event_task
                    return False
                
                # Store result
                self._task_results[state] = result
                
                # Advance to next state
                await self.advance_to_next_state()
                
                # Small delay to allow state transition to complete
                await asyncio.sleep(2)
            
            # Stop event processor
            self._running = False
            await event_task
            
            return True
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            await self.emit_event('fail', error=str(e))
            self._running = False
            return False
    
    async def execute_next_step(self, worker_manager):
        """
        Execute only the next step in the workflow.
        Used for manual step-by-step execution.
        
        Args:
            worker_manager: WorkerManager instance for executing tasks
        """
        try:
            current_state = self.state
            
            # Check if in terminal state
            if current_state in ['COMPLETE', 'FAILED', 'CANCELLED']:
                logger.warning(f"Cannot execute next step from terminal state: {current_state}")
                return False
            
            # Start event processor
            event_task = asyncio.create_task(self.process_events())
            
            # Get task type for current state
            task_type = self.STATE_TASKS.get(current_state, 'default')
            
            logger.info(f"Executing next step: {task_type} for state {current_state}")
            
            # Submit task to worker manager
            task_config = {
                'workflow_id': self.workflow_id,
                'state': current_state,
                'task_type': task_type
            }
            
            # Execute task in thread pool
            future = worker_manager.submit_workflow_task(
                self.workflow_id, 
                task_type, 
                task_config,
                self.db
            )
            
            # Wait for task completion
            result = await asyncio.get_event_loop().run_in_executor(None, future.result)
            
            if not result.get('success', False):
                # Task failed
                error = result.get('error', 'Task execution failed')
                await self.emit_event('fail', error=error)
                self._running = False
                await event_task
                return False
            
            # Store result
            self._task_results[current_state] = result
            
            # Advance to next state
            await self.advance_to_next_state()
            
            # Stop event processor
            self._running = False
            await event_task
            
            return True
            
        except Exception as e:
            logger.error(f"Next step execution error: {e}")
            await self.emit_event('fail', error=str(e))
            self._running = False
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        # Refresh workflow data
        self.workflow = self.workflow_dao.get_by_id(self.workflow_id)
        
        # Get all transitions for history
        transitions = self.transition_dao.get_by_workflow_id(self.workflow_id)
        
        return {
            "workflow_id": self.workflow_id,
            "name": self.workflow.name,
            "status": self.workflow.status.value,
            "current_state": self.workflow.current_state,
            "retries": self.workflow.retries,
            "started_at": self.workflow.started_at.isoformat() if self.workflow.started_at else None,
            "completed_at": self.workflow.completed_at.isoformat() if self.workflow.completed_at else None,
            "error_message": self.workflow.error_message,
            "next_trigger": self.get_next_trigger(),
            "transitions": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "trigger": t.trigger,
                    "timestamp": t.created_at.isoformat()
                }
                for t in transitions
            ],
            "task_results": self._task_results
        }
