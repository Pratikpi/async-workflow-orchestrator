"""Workflow API endpoints matching the specification."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from src.db import get_db, Workflow, WorkflowStatus, WorkflowTransition
from src.api.schemas import WorkflowCreate, WorkflowResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/start", response_model=dict, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    workflow: WorkflowCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start a new workflow.
    Creates workflow in INIT state and kicks off orchestrator.
    
    POST /workflow/start
    """
    # Create workflow in INIT state
    db_workflow = Workflow(
        name=workflow.name,
        description=workflow.description,
        config=workflow.config,
        status=WorkflowStatus.INIT,
        current_state="INIT",
        retries=0
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    
    logger.info(f"Created workflow {db_workflow.id}: {db_workflow.name} in INIT state")
    
    # Execute workflow in background
    from src.api.execution import execute_workflow_background
    background_tasks.add_task(execute_workflow_background, db_workflow.id)
    
    return {
        "message": "Workflow started",
        "workflow_id": db_workflow.id,
        "name": db_workflow.name,
        "status": db_workflow.status.value,
        "current_state": db_workflow.current_state
    }


@router.get("/{workflow_id}", response_model=dict)
def get_workflow_state(workflow_id: int, db: Session = Depends(get_db)):
    """
    Get current workflow state and full history.
    
    GET /workflow/{id}
    """
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Get all transitions for history
    transitions = db.query(WorkflowTransition).filter(
        WorkflowTransition.workflow_id == workflow_id
    ).order_by(WorkflowTransition.created_at).all()
    
    # Get status from orchestrator
    from src.core import WorkflowOrchestrator
    try:
        orchestrator = WorkflowOrchestrator(workflow_id, db)
        status_info = orchestrator.get_status()
    except Exception as e:
        logger.error(f"Error getting orchestrator status: {e}")
        status_info = {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "current_state": workflow.current_state,
            "retries": workflow.retries,
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "error_message": workflow.error_message,
            "transitions": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "trigger": t.trigger,
                    "timestamp": t.created_at.isoformat()
                }
                for t in transitions
            ]
        }
    
    return status_info


@router.post("/{workflow_id}/next", response_model=dict)
async def trigger_next_step(
    workflow_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Manually trigger the next step in the workflow.
    
    POST /workflow/{id}/next
    """
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Check if workflow is in a state that can progress
    if workflow.status in [WorkflowStatus.COMPLETE, WorkflowStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow in terminal state '{workflow.status.value}' cannot progress"
        )
    
    if workflow.status == WorkflowStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has failed. Use /retry endpoint to restart"
        )
    
    logger.info(f"Triggering next step for workflow {workflow_id}")
    
    # Execute next step in background
    from src.api.execution import execute_next_step_background
    background_tasks.add_task(execute_next_step_background, workflow_id)
    
    return {
        "message": f"Next step triggered for workflow {workflow_id}",
        "workflow_id": workflow_id,
        "current_state": workflow.current_state,
        "status": workflow.status.value
    }


@router.post("/{workflow_id}/retry", response_model=dict)
async def retry_workflow(
    workflow_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Retry a failed workflow from the beginning.
    
    POST /workflow/{id}/retry
    """
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Check if workflow is in FAILED state
    if workflow.status != WorkflowStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only retry FAILED workflows. Current status: {workflow.status.value}"
        )
    
    logger.info(f"Retrying workflow {workflow_id} (attempt {workflow.retries + 1})")
    
    # Create orchestrator and trigger retry
    from src.core import WorkflowOrchestrator
    orchestrator = WorkflowOrchestrator(workflow_id, db)
    
    # Use synchronous retry trigger
    orchestrator.retry()
    
    # Execute workflow in background
    from src.api.execution import execute_workflow_background
    background_tasks.add_task(execute_workflow_background, workflow_id)
    
    return {
        "message": f"Workflow {workflow_id} retry initiated",
        "workflow_id": workflow_id,
        "retries": workflow.retries,
        "current_state": workflow.current_state,
        "status": workflow.status.value
    }


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """
    Delete a workflow and all its history.
    
    DELETE /workflow/{id}
    """
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Don't allow deletion of running workflows
    if workflow.status in [WorkflowStatus.INIT, WorkflowStatus.PREPARE, 
                           WorkflowStatus.EXECUTE, WorkflowStatus.VALIDATE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running workflow"
        )
    
    db.delete(workflow)
    db.commit()
    
    logger.info(f"Deleted workflow {workflow_id}")
    return None
