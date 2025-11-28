"""FastAPI route handlers for workflow management."""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db import get_db, Workflow, Task, WorkflowTransition, WorkflowStatus, TaskStatus
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
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    """Create a new workflow."""
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
    
    logger.info(f"Created workflow {db_workflow.id}: {db_workflow.name}")
    return db_workflow


@router.get("/", response_model=List[WorkflowResponse])
def list_workflows(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_db)
):
    """List all workflows with optional filtering."""
    query = db.query(Workflow)
    
    if status_filter:
        try:
            status_enum = WorkflowStatus(status_filter)
            query = query.filter(Workflow.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    workflows = query.offset(skip).limit(limit).all()
    return workflows


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Get a specific workflow by ID."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
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
    db: Session = Depends(get_db)
):
    """Update a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
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
    
    # Update fields
    if workflow_update.name is not None:
        workflow.name = workflow_update.name
    if workflow_update.description is not None:
        workflow.description = workflow_update.description
    if workflow_update.config is not None:
        workflow.config = workflow_update.config
    
    db.commit()
    db.refresh(workflow)
    
    logger.info(f"Updated workflow {workflow_id}")
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Delete a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
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
    
    db.delete(workflow)
    db.commit()
    
    logger.info(f"Deleted workflow {workflow_id}")
    return None


@router.get("/{workflow_id}/tasks", response_model=List[TaskResponse])
def get_workflow_tasks(workflow_id: int, db: Session = Depends(get_db)):
    """Get all tasks for a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    tasks = db.query(Task).filter(Task.workflow_id == workflow_id).all()
    return tasks


@router.get("/{workflow_id}/transitions", response_model=List[TransitionResponse])
def get_workflow_transitions(workflow_id: int, db: Session = Depends(get_db)):
    """Get all state transitions for a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    transitions = db.query(WorkflowTransition).filter(
        WorkflowTransition.workflow_id == workflow_id
    ).order_by(WorkflowTransition.created_at).all()
    
    return transitions
