"""Worker manager for parallel task execution using threads and queue."""
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from src.db import Task, TaskStatus, SessionLocal as DefaultSessionLocal


logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manages parallel task execution using a thread pool and queue.Queue.
    """
    
    def __init__(self, max_workers: Optional[int] = None, session_factory: Optional[sessionmaker] = None):
        """
        Initialize the worker manager.
        
        Args:
            max_workers: Maximum number of worker threads (default from settings)
            session_factory: Optional session factory for database access (for testing)
        """
        self.max_workers = max_workers or settings.max_workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.task_queue = queue.Queue()
        self.active_tasks: Dict[int, Future] = {}
        self._shutdown = False
        self.session_factory = session_factory or DefaultSessionLocal
        
        logger.info(f"WorkerManager initialized with {self.max_workers} workers")
    
    def submit_workflow_task(self, workflow_id: int, task_type: str, task_config: Dict[str, Any], db: Session) -> Future:
        """
        Submit a workflow state task for execution.
        
        Args:
            workflow_id: ID of the workflow
            task_type: Type of task to execute
            task_config: Task configuration
            db: Database session
            
        Returns:
            Future object representing the task execution
        """
        logger.info(f"Submitting workflow task {task_type} for workflow {workflow_id}")
        
        # Submit task to thread pool
        future = self.executor.submit(self._execute_workflow_task, workflow_id, task_type, task_config)
        
        return future
    
    def _execute_workflow_task(self, workflow_id: int, task_type: str, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow state task (runs in worker thread).
        
        Args:
            workflow_id: ID of the workflow
            task_type: Type of task to execute
            task_config: Task configuration
            
        Returns:
            Task execution result with success flag
        """
        try:
            logger.info(f"Executing workflow task {task_type} for workflow {workflow_id} in thread {threading.current_thread().name}")
            
            # Execute task logic based on task type
            result = self._run_workflow_task_logic(task_type, task_config)
            
            logger.info(f"Workflow task {task_type} completed successfully")
            return {"success": True, "result": result, "task_type": task_type}
            
        except Exception as e:
            logger.error(f"Workflow task {task_type} failed: {e}")
            return {"success": False, "error": str(e), "task_type": task_type}
    
    def _run_workflow_task_logic(self, task_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the actual workflow task logic based on task type.
        
        Args:
            task_type: Type of task to execute
            config: Task configuration
            
        Returns:
            Task execution result
        """
        logger.debug(f"Running workflow task type: {task_type} with config: {config}")
        
        # Task implementations for each workflow state
        if task_type == "initialize":
            # INIT state: Set up initial resources
            time.sleep(0.5)  # Simulate initialization
            return {
                "status": "initialized",
                "message": "Workflow resources initialized",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        elif task_type == "prepare":
            # PREPARE state: Prepare data and resources
            time.sleep(0.7)  # Simulate preparation
            return {
                "status": "prepared",
                "message": "Data and resources prepared",
                "files_created": 3,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        elif task_type == "execute":
            # EXECUTE state: Run main computation
            iterations = config.get("iterations", 5000)
            result = sum(i * i for i in range(iterations))
            time.sleep(1.0)  # Simulate heavy computation
            return {
                "status": "executed",
                "message": "Main computation completed",
                "computation_result": result,
                "iterations": iterations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        elif task_type == "validate":
            # VALIDATE state: Validate results
            time.sleep(0.6)  # Simulate validation
            validation_passed = True  # In real scenario, would check actual results
            return {
                "status": "validated",
                "message": "Results validated successfully",
                "validation_passed": validation_passed,
                "checks_performed": 5,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        elif task_type == "complete":
            # COMPLETE state: Finalize workflow
            time.sleep(0.3)  # Simulate finalization
            return {
                "status": "completed",
                "message": "Workflow finalized",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        else:
            # Default task execution
            logger.warning(f"Unknown workflow task type: {task_type}, executing as default")
            time.sleep(0.5)
            return {
                "status": "success",
                "task_type": task_type,
                "message": "Default task execution",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def submit_task(self, task_id: int, db: Session) -> Future:
        """
        Submit a task for execution.
        
        Args:
            task_id: ID of the task to execute
            db: Database session
            
        Returns:
            Future object representing the task execution
        """
        # Load task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Update task status to queued
        task.status = TaskStatus.QUEUED
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Submitting task {task_id} ({task.name}) to worker pool")
        
        # Submit task to thread pool
        future = self.executor.submit(self._execute_task, task_id)
        self.active_tasks[task_id] = future
        
        return future
    
    def _execute_task(self, task_id: int) -> bool:
        """
        Execute a single task (runs in worker thread).
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            True if task succeeded, False otherwise
        """
        # Create new database session for this thread
        db = self.session_factory()
        
        try:
            # Load task
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return False
            
            # Update status to running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            task.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Executing task {task_id} ({task.name}) in thread {threading.current_thread().name}")
            
            # Execute task based on task type
            result = self._run_task_logic(task)
            
            # Update task with result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.updated_at = datetime.now(timezone.utc)
            task.result = result
            db.commit()
            
            logger.info(f"Task {task_id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            
            # Update task status to failed
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)
                task.updated_at = datetime.now(timezone.utc)
                task.error_message = str(e)
                db.commit()
            
            return False
            
        finally:
            db.close()
            # Remove from active tasks
            self.active_tasks.pop(task_id, None)
    
    def _run_task_logic(self, task: Task) -> Dict[str, Any]:
        """
        Execute the actual task logic based on task type.
        
        This is a placeholder implementation. In production, you would
        implement specific task handlers based on task_type.
        
        Args:
            task: Task object to execute
            
        Returns:
            Task execution result
        """
        task_type = task.task_type
        config = task.config or {}
        
        logger.debug(f"Running task type: {task_type} with config: {config}")
        
        # Simulate task execution
        if task_type == "sleep":
            # Simple sleep task for testing
            duration = config.get("duration", 1)
            time.sleep(duration)
            return {"status": "success", "duration": duration}
        
        elif task_type == "compute":
            # Simulate computation
            iterations = config.get("iterations", 1000)
            result = sum(i * i for i in range(iterations))
            return {"status": "success", "result": result}
        
        elif task_type == "http_request":
            # Placeholder for HTTP request
            # In production, use requests or httpx
            url = config.get("url", "")
            return {"status": "success", "url": url, "simulated": True}
        
        else:
            # Default task execution
            logger.warning(f"Unknown task type: {task_type}, executing as no-op")
            return {"status": "success", "task_type": task_type}
    
    def get_queue_size(self) -> int:
        """Get the number of tasks in the queue."""
        return self.task_queue.qsize()
    
    def get_active_count(self) -> int:
        """Get the number of currently executing tasks."""
        return len(self.active_tasks)
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the worker manager.
        
        Args:
            wait: Whether to wait for tasks to complete
        """
        logger.info("Shutting down WorkerManager")
        self._shutdown = True
        self.executor.shutdown(wait=wait)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
