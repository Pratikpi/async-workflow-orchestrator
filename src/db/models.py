"""Database models for workflow orchestration."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import declarative_base, relationship
import enum


Base = declarative_base()


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status."""
    INIT = "INIT"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"
    VALIDATE = "VALIDATE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskStatus(str, enum.Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Workflow(Base):
    """Workflow definition and execution tracking."""
    __tablename__ = "workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.INIT, nullable=False)
    current_state = Column(String(50), default="INIT", nullable=False)  # Current workflow state
    config = Column(JSON, nullable=True)  # Workflow configuration and metadata
    retries = Column(Integer, default=0, nullable=False)  # Number of retry attempts
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="workflow", cascade="all, delete-orphan")
    transitions = relationship("WorkflowTransition", back_populates="workflow", cascade="all, delete-orphan")


class Task(Base):
    """Individual task within a workflow."""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    task_type = Column(String(100), nullable=False)  # e.g., 'http_request', 'data_processing'
    config = Column(JSON, nullable=True)  # Task-specific configuration
    result = Column(JSON, nullable=True)  # Task execution result
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="tasks")


class WorkflowTransition(Base):
    """State machine transitions for workflow tracking."""
    __tablename__ = "workflow_transitions"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    from_state = Column(String(50), nullable=False)
    to_state = Column(String(50), nullable=False)
    trigger = Column(String(100), nullable=True)  # What triggered the transition
    transition_metadata = Column(JSON, nullable=True)  # Additional transition information
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="transitions")
