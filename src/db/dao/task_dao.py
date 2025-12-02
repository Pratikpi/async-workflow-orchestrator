from typing import List, Optional, Any, Dict
from sqlalchemy.orm import Session
from src.db.models import Task, TaskStatus

class TaskDAO:
    def __init__(self, db: Session):
        self.db = db

    def create(self, task: Task) -> Task:
        """Create a new task."""
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """Get a task by its ID."""
        return self.db.query(Task).filter(Task.id == task_id).first()

    def get_by_workflow_id(self, workflow_id: int) -> List[Task]:
        """Get all tasks for a specific workflow."""
        return self.db.query(Task).filter(Task.workflow_id == workflow_id).all()

    def list_tasks(self, skip: int = 0, limit: int = 100) -> List[Task]:
        """List tasks with pagination."""
        return self.db.query(Task).offset(skip).limit(limit).all()

    def update(self, task_id: int, update_data: Dict[str, Any]) -> Optional[Task]:
        """
        Update a task.
        
        Args:
            task_id: The ID of the task to update.
            update_data: A dictionary of attributes to update.
        """
        task = self.get_by_id(task_id)
        if not task:
            return None
            
        for key, value in update_data.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task_id: int) -> bool:
        """Delete a task by ID."""
        task = self.get_by_id(task_id)
        if not task:
            return False
            
        self.db.delete(task)
        self.db.commit()
        return True
