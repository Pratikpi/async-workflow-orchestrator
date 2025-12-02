"""Workflow API endpoints matching the specification."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from src.db import get_db, Workflow, WorkflowStatus, WorkflowTransition
from src.api.schemas import WorkflowCreate, WorkflowResponse, WorkflowStatusDetail
from src.db.dao.workflow_dao import WorkflowDAO
from src.db.dao.workflow_transition_dao import WorkflowTransitionDAO
from src.api.dependencies import get_workflow_dao, get_workflow_transition_dao


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/start", response_model=dict, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    workflow: WorkflowCreate,
    background_tasks: BackgroundTasks,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
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
    db_workflow = workflow_dao.create(db_workflow)
    
    logger.info(f"Created workflow {db_workflow.id}: {db_workflow.name} in INIT state")
    
    # Execute workflow in background if auto_start is True
    if workflow.auto_start:
        from src.api.execution import execute_workflow_background
        background_tasks.add_task(execute_workflow_background, db_workflow.id)
    
    return {
        "message": "Workflow started",
        "workflow_id": db_workflow.id,
        "name": db_workflow.name,
        "status": db_workflow.status.value,
        "current_state": db_workflow.current_state
    }


@router.get("/{workflow_id}", response_model=WorkflowStatusDetail)
def get_workflow_state(
    workflow_id: int,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao),
    transition_dao: WorkflowTransitionDAO = Depends(get_workflow_transition_dao),
    db: Session = Depends(get_db)
):
    """
    Get current workflow state and full history.
    
    GET /workflow/{id}
    """
    # Verify workflow exists
    workflow = workflow_dao.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Get status from orchestrator
    from src.core import WorkflowOrchestrator
    try:
        orchestrator = WorkflowOrchestrator(workflow_id, db)
        status_info = orchestrator.get_status()
    except Exception as e:
        logger.error(f"Error getting orchestrator status: {e}")
        # Fallback to DB data if orchestrator fails
        transitions = transition_dao.get_by_workflow_id(workflow_id)
        status_info = {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status.value,
            "current_state": workflow.current_state,
            "retries": workflow.retries,
            "started_at": workflow.started_at,
            "completed_at": workflow.completed_at,
            "error_message": workflow.error_message,
            "next_trigger": None,
            "transitions": transitions,
            "task_results": {}
        }
    
    return status_info


@router.post("/{workflow_id}/next", response_model=dict)

async def trigger_next_step(
    workflow_id: int,
    background_tasks: BackgroundTasks,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """
    Manually trigger the next step in the workflow.
    
    POST /workflow/{id}/next
    """
    # Verify workflow exists
    workflow = workflow_dao.get_by_id(workflow_id)
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
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao),
    db: Session = Depends(get_db)
):
    """
    Retry a failed workflow from the beginning.
    
    POST /workflow/{id}/retry
    """
    # Verify workflow exists
    workflow = workflow_dao.get_by_id(workflow_id)
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

def delete_workflow(
    workflow_id: int,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """
    Delete a workflow and all its history.
    
    DELETE /workflow/{id}
    """
    workflow = workflow_dao.get_by_id(workflow_id)
    
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
    
    workflow_dao.delete(workflow_id)
    
    logger.info(f"Deleted workflow {workflow_id}")
    return None
