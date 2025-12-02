"""FastAPI route handlers for workflow management."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db import get_db, Workflow, Task, WorkflowTransition, WorkflowStatus, TaskStatus
from src.db.dao.workflow_dao import WorkflowDAO
from src.db.dao.task_dao import TaskDAO
from src.db.dao.workflow_transition_dao import WorkflowTransitionDAO
from src.api.dependencies import get_workflow_dao, get_task_dao, get_workflow_transition_dao
from .schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    TaskCreate,
    TaskResponse,
    TransitionResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow: WorkflowCreate,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """Create a new workflow."""
    db_workflow = Workflow(
        name=workflow.name,
        description=workflow.description,
        config=workflow.config,
        status=WorkflowStatus.INIT,
        current_state="INIT",
        retries=0
    )
    db_workflow = workflow_dao.create(db_workflow)
    
    logger.info(f"Created workflow {db_workflow.id}: {db_workflow.name}")
    return db_workflow


@router.get("/", response_model=List[WorkflowResponse])
def list_workflows(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """List all workflows with optional filtering."""
    workflows: List[Workflow] = workflow_dao.list_workflows(skip=skip, limit=limit)
    
    if status_filter:
        try:
            status_enum = WorkflowStatus(status_filter)
            workflows = [w for w in workflows if w.status == status_enum]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
            
    return workflows


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: int,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """Get a specific workflow by ID."""
    workflow = workflow_dao.get_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """Update a workflow."""
    workflow = workflow_dao.get_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Only allow updates if workflow is not running
    if workflow.status in [WorkflowStatus.PREPARE, WorkflowStatus.EXECUTE, WorkflowStatus.VALIDATE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a running workflow"
        )
    
    # Prepare update data
    update_data = {}
    if workflow_update.name is not None:
        update_data["name"] = workflow_update.name
    if workflow_update.description is not None:
        update_data["description"] = workflow_update.description
    if workflow_update.config is not None:
        update_data["config"] = workflow_update.config
    
    if update_data:
        workflow = workflow_dao.update(workflow_id, update_data)
    
    logger.info(f"Updated workflow {workflow_id}")
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: int,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """Delete a workflow."""
    workflow = workflow_dao.get_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Don't allow deletion of running workflows
    if workflow.status in [WorkflowStatus.PREPARE, WorkflowStatus.EXECUTE, WorkflowStatus.VALIDATE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running workflow"
        )
    
    workflow_dao.delete(workflow_id)
    
    logger.info(f"Deleted workflow {workflow_id}")
    return None


@router.get("/{workflow_id}/tasks", response_model=List[TaskResponse])
def get_workflow_tasks(
    workflow_id: int,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao),
    task_dao: TaskDAO = Depends(get_task_dao)
):
    """Get all tasks for a workflow."""
    workflow = workflow_dao.get_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    tasks = task_dao.get_by_workflow_id(workflow_id)
    return tasks


@router.get("/{workflow_id}/transitions", response_model=List[TransitionResponse])
def get_workflow_transitions(
    workflow_id: int,
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao),
    transition_dao: WorkflowTransitionDAO = Depends(get_workflow_transition_dao)
):
    """Get all state transitions for a workflow."""
    workflow = workflow_dao.get_by_id(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    transitions = transition_dao.get_by_workflow_id(workflow_id)
    
    return transitions
