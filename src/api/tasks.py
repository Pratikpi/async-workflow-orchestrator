"""Task-related API endpoints."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db import get_db, Task, Workflow, TaskStatus
from src.db.dao.task_dao import TaskDAO
from src.db.dao.workflow_dao import WorkflowDAO
from src.api.dependencies import get_task_dao, get_workflow_dao
from .schemas import TaskCreate, TaskResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    task_dao: TaskDAO = Depends(get_task_dao),
    workflow_dao: WorkflowDAO = Depends(get_workflow_dao)
):
    """Create a new task for a workflow."""
    # Verify workflow exists
    workflow = workflow_dao.get_by_id(task.workflow_id)
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
    db_task = task_dao.create(db_task)
    
    logger.info(f"Created task {db_task.id}: {db_task.name} for workflow {task.workflow_id}")
    return db_task


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    workflow_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    task_dao: TaskDAO = Depends(get_task_dao)
):
    """List all tasks with optional filtering."""
    if workflow_id:
        tasks = task_dao.get_by_workflow_id(workflow_id)
    else:
        tasks = task_dao.list(skip=skip, limit=limit)
    
    if status_filter:
        try:
            status_enum = TaskStatus(status_filter)
            tasks = [t for t in tasks if t.status == status_enum]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    task_dao: TaskDAO = Depends(get_task_dao)
):
    """Get a specific task by ID."""
    task = task_dao.get_by_id(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    task_dao: TaskDAO = Depends(get_task_dao)
):
    """Delete a task."""
    task = task_dao.get_by_id(task_id)
    
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
    
    task_dao.delete(task_id)
    
    logger.info(f"Deleted task {task_id}")
    return None

