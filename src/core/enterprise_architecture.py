"""
Enterprise MLOps System Architecture
Staff-Level Engineering Implementation with Council-Driven Design
"""

from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, Generic, Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from datetime import datetime
import logging
from contextlib import asynccontextmanager

# Type definitions for enterprise-grade type safety
T = TypeVar('T')
ModelType = TypeVar('ModelType')
PredictionType = TypeVar('PredictionType')

class SystemState(Enum):
    """System operational states"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"

class DeploymentStrategy(Enum):
    """Deployment strategies for model updates"""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    SHADOW = "shadow"

@dataclass(frozen=True)
class APIContract:
    """Immutable API contract definition"""
    version: str
    endpoints: Dict[str, Dict[str, Any]]
    rate_limits: Dict[str, int]
    authentication_required: bool
    deprecation_date: Optional[datetime] = None

@dataclass
class SystemMetrics:
    """Comprehensive system health metrics"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    request_rate: float = 0.0
    error_rate: float = 0.0
    model_accuracy: float = 0.0
    inference_latency_p95: float = 0.0
    drift_score: float = 0.0

# Protocol definitions for dependency injection and testability
class ModelRepository(Protocol):
    """Model storage and retrieval interface"""
    async def get_model(self, model_id: str, version: str) -> ModelType: ...
    async def store_model(self, model: ModelType, metadata: Dict[str, Any]) -> str: ...
    async def list_versions(self, model_id: str) -> List[str]: ...

class FeatureStore(Protocol):
    """Feature storage and serving interface"""
    async def get_features(self, entity_id: str, feature_names: List[str]) -> Dict[str, Any]: ...
    async def store_features(self, features: Dict[str, Any]) -> None: ...

class MetricsCollector(Protocol):
    """Metrics collection and monitoring interface"""
    async def record_metric(self, name: str, value: float, tags: Dict[str, str]) -> None: ...
    async def get_system_health(self) -> SystemMetrics: ...

class SecurityValidator(Protocol):
    """Security validation and audit interface"""
    async def validate_request(self, request: Any) -> bool: ...
    async def audit_log(self, action: str, user: str, details: Dict[str, Any]) -> None: ...

# Enterprise-grade base classes
class BaseMLOpsComponent(ABC):
    """Base class for all MLOps components with enterprise patterns"""
    
    def __init__(self, component_id: str, config: Dict[str, Any]):
        self.component_id = component_id
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{component_id}")
        self._state = SystemState.INITIALIZING
        self._metrics: SystemMetrics = SystemMetrics()
    
    @property
    def state(self) -> SystemState:
        return self._state
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize component with proper error handling"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check with detailed diagnostics"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Graceful shutdown with cleanup"""
        pass
    
    async def update_state(self, new_state: SystemState) -> None:
        """Thread-safe state updates with logging"""
        old_state = self._state
        self._state = new_state
        self.logger.info(f"State transition: {old_state} -> {new_state}")

# Custom exceptions for proper error handling
class MLOpsError(Exception):
    """Base exception for MLOps operations"""
    pass

class SecurityError(MLOpsError):
    """Security validation failed"""
    pass

class RateLimitError(MLOpsError):
    """Rate limit exceeded"""
    pass

class InferenceError(MLOpsError):
    """Inference operation failed"""
    pass

class InferenceTimeoutError(InferenceError):
    """Inference operation timed out"""
    pass