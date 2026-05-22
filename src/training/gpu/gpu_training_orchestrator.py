"""
GPU Training Orchestrator
Manages training jobs on cloud (Azure ML, AWS SageMaker) and on-premise GPU resources
with job queuing, scheduling, and cost monitoring.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComputeTarget(Enum):
    LOCAL_CPU = "local_cpu"
    LOCAL_GPU = "local_gpu"
    AZURE_ML_GPU = "azure_ml_gpu"
    AWS_SAGEMAKER = "aws_sagemaker"
    ON_PREMISE_GPU = "on_premise_gpu"


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GPUConfig:
    """GPU compute configuration."""

    compute_target: ComputeTarget = ComputeTarget.AZURE_ML_GPU
    gpu_type: str = "NVIDIA_T4"
    num_gpus: int = 1
    max_runtime_hours: float = 4.0
    cost_per_hour: float = 2.50
    priority: int = 5  # 1=highest, 10=lowest
    preemptible: bool = False  # Use spot instances


@dataclass
class TrainingJob:
    """Represents a training job in the queue."""

    job_id: str
    model_type: str
    config: GPUConfig
    status: JobStatus = JobStatus.QUEUED
    submitted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cost_usd: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)


class TrainingJobQueue:
    """Priority queue for training jobs with cost tracking."""

    def __init__(self, max_concurrent: int = 2, budget_limit_usd: float = 500.0):
        self.max_concurrent = max_concurrent
        self.budget_limit_usd = budget_limit_usd
        self.queue: List[TrainingJob] = []
        self.running: List[TrainingJob] = []
        self.completed: List[TrainingJob] = []
        self.total_cost_usd = 0.0

    def submit_job(self, job: TrainingJob) -> str:
        """Submit a training job to the queue."""
        if self.total_cost_usd + self._estimate_cost(job) > self.budget_limit_usd:
            raise ValueError(
                f"Budget limit exceeded. Current: ${self.total_cost_usd:.2f}, "
                f"Limit: ${self.budget_limit_usd:.2f}"
            )

        self.queue.append(job)
        self.queue.sort(key=lambda j: j.config.priority)
        logger.info(f"Job {job.job_id} queued. Position: {len(self.queue)}")
        return job.job_id

    def process_queue(self):
        """Process next jobs in queue if capacity available."""
        while self.queue and len(self.running) < self.max_concurrent:
            job = self.queue.pop(0)
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow().isoformat()
            self.running.append(job)
            logger.info(f"Job {job.job_id} started on {job.config.compute_target.value}")

    def complete_job(self, job_id: str, metrics: Dict[str, float]):
        """Mark a job as completed and track cost."""
        for job in self.running:
            if job.job_id == job_id:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow().isoformat()
                job.metrics = metrics
                job.cost_usd = self._calculate_actual_cost(job)
                self.total_cost_usd += job.cost_usd
                self.running.remove(job)
                self.completed.append(job)
                logger.info(
                    f"Job {job_id} completed. Cost: ${job.cost_usd:.2f}"
                )
                return
        raise ValueError(f"Job {job_id} not found in running jobs")

    def get_cost_report(self) -> Dict[str, Any]:
        """Generate cost report for all training jobs."""
        return {
            "total_cost_usd": round(self.total_cost_usd, 2),
            "budget_remaining_usd": round(
                self.budget_limit_usd - self.total_cost_usd, 2
            ),
            "jobs_completed": len(self.completed),
            "jobs_running": len(self.running),
            "jobs_queued": len(self.queue),
            "cost_by_compute": self._cost_by_compute(),
            "avg_cost_per_job": round(
                self.total_cost_usd / max(len(self.completed), 1), 2
            ),
        }

    def _estimate_cost(self, job: TrainingJob) -> float:
        return job.config.max_runtime_hours * job.config.cost_per_hour

    def _calculate_actual_cost(self, job: TrainingJob) -> float:
        if job.started_at and job.completed_at:
            start = datetime.fromisoformat(job.started_at)
            end = datetime.fromisoformat(job.completed_at)
            hours = (end - start).total_seconds() / 3600
            return hours * job.config.cost_per_hour
        return self._estimate_cost(job)

    def _cost_by_compute(self) -> Dict[str, float]:
        costs = {}
        for job in self.completed:
            target = job.config.compute_target.value
            costs[target] = costs.get(target, 0) + job.cost_usd
        return costs


class GPUTrainingOrchestrator:
    """Orchestrates GPU training across cloud and on-premise resources."""

    def __init__(self, config: GPUConfig):
        self.config = config
        self.job_queue = TrainingJobQueue()

    def launch_training(
        self,
        model_type: str,
        training_params: Dict[str, Any],
        data_path: str,
    ) -> str:
        """Launch a training job on the configured compute target."""

        job_id = f"train_{model_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        job = TrainingJob(
            job_id=job_id,
            model_type=model_type,
            config=self.config,
        )

        if self.config.compute_target == ComputeTarget.AZURE_ML_GPU:
            self._launch_azure_ml(job, training_params, data_path)
        elif self.config.compute_target == ComputeTarget.AWS_SAGEMAKER:
            self._launch_sagemaker(job, training_params, data_path)
        elif self.config.compute_target == ComputeTarget.ON_PREMISE_GPU:
            self._launch_on_premise(job, training_params, data_path)
        else:
            self._launch_local(job, training_params, data_path)

        self.job_queue.submit_job(job)
        return job_id

    def _launch_azure_ml(
        self, job: TrainingJob, params: Dict, data_path: str
    ):
        """Launch training on Azure ML Compute with GPU."""
        from azureml.core import Environment, Experiment, ScriptRunConfig, Workspace
        from azureml.core.compute import AmlCompute, ComputeTarget as AzCompute

        ws = Workspace.from_config()

        # Get or create GPU compute cluster
        compute_name = "gpu-cluster"
        if compute_name not in ws.compute_targets:
            compute_config = AmlCompute.provisioning_configuration(
                vm_size="Standard_NC6s_v3",  # NVIDIA V100
                min_nodes=0,
                max_nodes=4,
                idle_seconds_before_scaledown=300,
            )
            AzCompute.create(ws, compute_name, compute_config)

        env = Environment.from_pip_requirements(
            "helios-grid-training", "requirements.txt"
        )

        src_config = ScriptRunConfig(
            source_directory="src/training",
            script="energy_model_training.py",
            compute_target=compute_name,
            environment=env,
            arguments=[
                "--model-type", job.model_type,
                "--data-path", data_path,
                "--n-trials", str(params.get("n_trials", 50)),
            ],
        )

        experiment = Experiment(ws, "helios-grid-training")
        run = experiment.submit(src_config)
        logger.info(f"Azure ML job submitted: {run.id}")

    def _launch_sagemaker(
        self, job: TrainingJob, params: Dict, data_path: str
    ):
        """Launch training on AWS SageMaker with GPU."""
        import sagemaker
        from sagemaker.estimator import Estimator

        session = sagemaker.Session()
        role = sagemaker.get_execution_role()

        estimator = Estimator(
            image_uri=f"763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.0.0-gpu-py310",
            role=role,
            instance_count=1,
            instance_type="ml.g4dn.xlarge",
            output_path=f"s3://helios-grid-models/training-output",
            max_run=int(self.config.max_runtime_hours * 3600),
            hyperparameters={
                "model_type": job.model_type,
                "n_trials": params.get("n_trials", 50),
            },
            use_spot_instances=self.config.preemptible,
            max_wait=int(self.config.max_runtime_hours * 3600 * 1.5),
        )

        estimator.fit({"training": data_path}, wait=False)
        logger.info(f"SageMaker job submitted: {estimator.latest_training_job.name}")

    def _launch_on_premise(
        self, job: TrainingJob, params: Dict, data_path: str
    ):
        """Launch training on on-premise GPU cluster via SSH/Docker."""
        import subprocess

        cmd = [
            "docker", "run", "--gpus", f'"device={self.config.num_gpus - 1}"',
            "--rm",
            "-v", f"{data_path}:/data",
            "-v", "./models:/models",
            "helios-grid-training:latest",
            "python", "energy_model_training.py",
            "--model-type", job.model_type,
            "--n-trials", str(params.get("n_trials", 50)),
        ]

        subprocess.Popen(cmd)
        logger.info(f"On-premise GPU job launched: {job.job_id}")

    def _launch_local(
        self, job: TrainingJob, params: Dict, data_path: str
    ):
        """Launch training locally (CPU or single GPU)."""
        logger.info(f"Local training job: {job.job_id}")
