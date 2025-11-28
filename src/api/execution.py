"""Workflow execution endpoints."""
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from config import settings
from src.db import get_db, Workflow, WorkflowStatus
from src.core import WorkflowOrchestrator, WorkerManager
from .schemas import WorkflowExecutionResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/execution", tags=["execution"])

# Global worker manager (initialized at startup)
_worker_manager = None


def get_worker_manager() -> WorkerManager:
    """Get the global worker manager instance."""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager(max_workers=settings.max_workers)
    return _worker_manager


async def execute_workflow_background(workflow_id: int):
    """Execute workflow in the background (automatic execution through all states)."""
    db = None
    try:
        from src.db import SessionLocal
        db = SessionLocal()
        
        orchestrator = WorkflowOrchestrator(workflow_id, db)
        worker_manager = get_worker_manager()
        
        await orchestrator.execute_automatic(worker_manager)
        
    except Exception as e:
        logger.error(f"Background workflow execution error: {e}")
    finally:
        if db:
            db.close()


async def execute_next_step_background(workflow_id: int):
    """Execute only the next step of workflow in the background."""
    db = None
    try:
        from src.db import SessionLocal
        db = SessionLocal()
        
        orchestrator = WorkflowOrchestrator(workflow_id, db)
        worker_manager = get_worker_manager()
        
        await orchestrator.execute_next_step(worker_manager)
        
    except Exception as e:
        logger.error(f"Background next step execution error: {e}")
    finally:
        if db:
            db.close()


@router.post("/workflows/{workflow_id}/start", response_model=WorkflowExecutionResponse)
async def start_workflow(
    workflow_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start workflow execution."""
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Check if workflow can be started
    if workflow.status not in [WorkflowStatus.INIT, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow in status '{workflow.status.value}' cannot be started"
        )
    
    # Reset workflow status to INIT if it was failed/cancelled
    if workflow.status in [WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
        workflow.status = WorkflowStatus.INIT
        workflow.current_state = "INIT"
        db.commit()
    
    logger.info(f"Starting workflow {workflow_id}")
    
    # Execute workflow in background
    background_tasks.add_task(execute_workflow_background, workflow_id)
    
    # Create orchestrator to get initial status
    orchestrator = WorkflowOrchestrator(workflow_id, db)
    status_info = orchestrator.get_status()
    
    return WorkflowExecutionResponse(**status_info)


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowExecutionResponse)
def get_workflow_status(workflow_id: int, db: Session = Depends(get_db)):
    """Get current workflow execution status."""
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Get status from orchestrator
    orchestrator = WorkflowOrchestrator(workflow_id, db)
    status_info = orchestrator.get_status()
    
    return WorkflowExecutionResponse(**status_info)


@router.post("/workflows/{workflow_id}/cancel", response_model=Dict[str, Any])
async def cancel_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Cancel a running workflow."""
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Check if workflow is running
    if workflow.status not in [WorkflowStatus.INIT, WorkflowStatus.PREPARE, WorkflowStatus.EXECUTE, WorkflowStatus.VALIDATE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow in status '{workflow.status.value}' cannot be cancelled"
        )
    
    logger.info(f"Cancelling workflow {workflow_id}")
    
    # Create orchestrator and emit cancel event
    orchestrator = WorkflowOrchestrator(workflow_id, db)
    await orchestrator.emit_event('cancel')
    
    # Process the event
    orchestrator._running = True
    await asyncio.wait_for(orchestrator.process_events(), timeout=2.0)
    
    return {"message": f"Workflow {workflow_id} cancelled", "status": "cancelled"}


@router.get("/stats", response_model=Dict[str, Any])
def get_execution_stats(db: Session = Depends(get_db)):
    """Get execution statistics."""
    worker_manager = get_worker_manager()
    
    # Count workflows by status
    from src.db import Workflow
    total_workflows = db.query(Workflow).count()
    init = db.query(Workflow).filter(Workflow.status == WorkflowStatus.INIT).count()
    prepare = db.query(Workflow).filter(Workflow.status == WorkflowStatus.PREPARE).count()
    execute = db.query(Workflow).filter(Workflow.status == WorkflowStatus.EXECUTE).count()
    validate = db.query(Workflow).filter(Workflow.status == WorkflowStatus.VALIDATE).count()
    complete = db.query(Workflow).filter(Workflow.status == WorkflowStatus.COMPLETE).count()
    failed = db.query(Workflow).filter(Workflow.status == WorkflowStatus.FAILED).count()
    cancelled = db.query(Workflow).filter(Workflow.status == WorkflowStatus.CANCELLED).count()
    
    return {
        "worker_pool": {
            "max_workers": worker_manager.max_workers,
            "active_tasks": worker_manager.get_active_count(),
            "queue_size": worker_manager.get_queue_size(),
        },
        "workflows": {
            "total": total_workflows,
            "init": init,
            "prepare": prepare,
            "execute": execute,
            "validate": validate,
            "complete": complete,
            "failed": failed,
            "cancelled": cancelled
        }
    }
