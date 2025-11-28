"""Task-related API endpoints."""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db import get_db, Task, Workflow, TaskStatus
from .schemas import TaskCreate, TaskResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task for a workflow."""
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == task.workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {task.workflow_id} not found"
        )
    
    db_task = Task(
        workflow_id=task.workflow_id,
        name=task.name,
        description=task.description,
        task_type=task.task_type,
        config=task.config,
        status=TaskStatus.PENDING,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    logger.info(f"Created task {db_task.id}: {db_task.name} for workflow {task.workflow_id}")
    return db_task


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    workflow_id: int = None,
    status_filter: str = None,
    db: Session = Depends(get_db)
):
    """List all tasks with optional filtering."""
    query = db.query(Task)
    
    if workflow_id:
        query = query.filter(Task.workflow_id == workflow_id)
    
    if status_filter:
        try:
            status_enum = TaskStatus(status_filter)
            query = query.filter(Task.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    # Don't allow deletion of running tasks
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running task"
        )
    
    db.delete(task)
    db.commit()
    
    logger.info(f"Deleted task {task_id}")
    return None
