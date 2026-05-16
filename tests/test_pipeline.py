"""
Comprehensive Test Suite for MLOps Pipeline
Tests data ingestion, feature engineering, model training, and API endpoints
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from fastapi.testclient import TestClient
import sys
sys.path.append('../src')

from src.data.kaggle_ingestion import KaggleDataIngestion, DatasetConfig
from src.features.feature_engineering import FeaturePipeline, FeatureConfig
from src.training.train_model import ModelTrainer, ModelConfig
from src.api.main import app
from src.monitoring.drift_detection import DriftDetector, ModelPerformanceMonitor

class TestDataIngestion:
    """Test data ingestion pipeline"""
    
    @pytest.fixture
    def sample_config(self):
        return DatasetConfig(
            name="test-dataset",
            competition_or_dataset="dataset",
            target_column="target",
            validation_rules={"missing_threshold": 0.3}
        )
    
    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': ['A', 'B', 'C', 'D', 'E'],
            'target': [10, 20, 30, 40, 50]
        })
    
    def test_dataset_config_creation(self, sample_config):
        """Test dataset configuration creation"""
        assert sample_config.name == "test-dataset"
        assert sample_config.target_column == "target"
        assert sample_config.validation_rules["missing_threshold"] == 0.3
    
    @patch('src.data.kaggle_ingestion.DefaultAzureCredential')
    @patch('src.data.kaggle_ingestion.BlobServiceClient')
    def test_azure_storage_setup(self, mock_blob_client, mock_credential, sample_config):
        """Test Azure storage client setup"""
        with patch.dict(os.environ, {'AZURE_STORAGE_ACCOUNT': 'test_account'}):
            ingestion = KaggleDataIngestion(sample_config)
            assert ingestion.blob_client is not None
    
    def test_data_validation_success(self, sample_config, sample_data):
        """Test successful data validation"""
        with patch('src.data.kaggle_ingestion.DefaultAzureCredential'):
            with patch('src.data.kaggle_ingestion.BlobServiceClient'):
                ingestion = KaggleDataIngestion(sample_config)
                
                # Mock Great Expectations
                with patch.object(ingestion, 'data_context') as mock_context:
                    mock_validator = Mock()
                    mock_validator.validate.return_value = Mock(success=True)
                    mock_context.get_validator.return_value = mock_validator
                    mock_context.add_or_update_expectation_suite.return_value = Mock()
                    
                    result = ingestion.validate_data(sample_data)
                    assert result is True
    
    def test_data_validation_failure(self, sample_config, sample_data):
        """Test data validation failure"""
        with patch('src.data.kaggle_ingestion.DefaultAzureCredential'):
            with patch('src.data.kaggle_ingestion.BlobServiceClient'):
                ingestion = KaggleDataIngestion(sample_config)
                
                # Mock Great Expectations failure
                with patch.object(ingestion, 'data_context') as mock_context:
                    mock_validator = Mock()
                    mock_validator.validate.return_value = Mock(success=False)
                    mock_context.get_validator.return_value = mock_validator
                    mock_context.add_or_update_expectation_suite.return_value = Mock()
                    
                    result = ingestion.validate_data(sample_data)
                    assert result is False

class TestFeatureEngineering:
    """Test feature engineering pipeline"""
    
    @pytest.fixture
    def sample_config(self):
        return FeatureConfig(
            numerical_features=['num1', 'num2'],
            categorical_features=['cat1', 'cat2'],
            target_column='target',
            feature_selection_k=5
        )
    
    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame({
            'num1': [1, 2, 3, 4, 5],
            'num2': [10, 20, 30, 40, 50],
            'cat1': ['A', 'B', 'C', 'A', 'B'],
            'cat2': ['X', 'Y', 'X', 'Y', 'X'],
            'target': [100, 200, 300, 400, 500]
        })
    
    def test_feature_config_creation(self, sample_config):
        """Test feature configuration creation"""
        assert len(sample_config.numerical_features) == 2
        assert len(sample_config.categorical_features) == 2
        assert sample_config.target_column == 'target'
    
    def test_feature_pipeline_initialization(self, sample_config):
        """Test feature pipeline initialization"""
        pipeline = FeaturePipeline(sample_config)
        assert pipeline.config == sample_config
        assert pipeline.feature_engineer is not None
    
    @patch('mlflow.start_run')
    @patch('mlflow.log_param')
    @patch('mlflow.log_metric')
    @patch('mlflow.sklearn.log_model')
    def test_feature_processing(self, mock_log_model, mock_log_metric, 
                               mock_log_param, mock_start_run, 
                               sample_config, sample_data):
        """Test feature processing pipeline"""
        mock_start_run.return_value.__enter__ = Mock()
        mock_start_run.return_value.__exit__ = Mock()
        
        pipeline = FeaturePipeline(sample_config)
        
        X_train, X_test, y_train = pipeline.process_features(sample_data)
        
        assert X_train is not None
        assert y_train is not None
        assert len(y_train) == len(sample_data)
    
    def test_feature_engineer_fit_transform(self, sample_config, sample_data):
        """Test feature engineer fit and transform"""
        from src.features.feature_engineering import AdvancedFeatureEngineer
        
        engineer = AdvancedFeatureEngineer(sample_config)
        
        X = sample_data.drop(columns=['target'])
        y = sample_data['target']
        
        engineer.fit(X, y)
        X_transformed = engineer.transform(X)
        
        assert X_transformed is not None
        assert X_transformed.shape[0] == len(X)

class TestModelTraining:
    """Test model training pipeline"""
    
    @pytest.fixture
    def sample_config(self):
        return ModelConfig(
            model_type='random_forest',
            cv_folds=3,
            n_trials=5,
            random_state=42
        )
    
    @pytest.fixture
    def sample_data(self):
        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = np.random.randn(100)
        return X, y
    
    def test_model_config_creation(self, sample_config):
        """Test model configuration creation"""
        assert sample_config.model_type == 'random_forest'
        assert sample_config.cv_folds == 3
        assert sample_config.n_trials == 5
    
    @patch('src.training.train_model.Workspace.from_config')
    def test_model_trainer_initialization(self, mock_workspace, sample_config):
        """Test model trainer initialization"""
        mock_workspace.return_value = Mock()
        trainer = ModelTrainer(sample_config)
        assert trainer.config == sample_config
    
    @patch('mlflow.start_run')
    @patch('mlflow.log_params')
    @patch('mlflow.log_metric')
    @patch('mlflow.sklearn.log_model')
    @patch('optuna.create_study')
    def test_model_training(self, mock_create_study, mock_log_model, 
                           mock_log_metric, mock_log_params, mock_start_run,
                           sample_config, sample_data):
        """Test model training process"""
        X, y = sample_data
        
        # Mock MLflow
        mock_start_run.return_value.__enter__ = Mock()
        mock_start_run.return_value.__exit__ = Mock()
        
        # Mock Optuna
        mock_study = Mock()
        mock_study.best_params = {'n_estimators': 100, 'max_depth': 5}
        mock_study.best_value = 0.1
        mock_create_study.return_value = mock_study
        
        with patch('src.training.train_model.Workspace.from_config'):
            trainer = ModelTrainer(sample_config)
            result = trainer.train_model(X, y)
        
        assert 'model' in result
        assert 'best_params' in result
        assert 'cv_rmse' in result
    
    def test_get_model_and_params(self, sample_config):
        """Test model and parameter retrieval"""
        with patch('src.training.train_model.Workspace.from_config'):
            trainer = ModelTrainer(sample_config)
            model, params = trainer._get_model_and_params()
        
        assert model is not None
        assert isinstance(params, dict)
        assert 'random_state' in params

class TestAPI:
    """Test FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_model_manager(self):
        with patch('src.api.main.model_manager') as mock:
            mock.model = Mock()
            mock.model_version = "test_v1"
            yield mock
    
    def test_health_endpoint(self, client, mock_model_manager):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "model_loaded" in data
    
    def test_predict_endpoint_success(self, client, mock_model_manager):
        """Test successful prediction"""
        mock_model_manager.predict.return_value = {
            'prediction': 100.0,
            'confidence_interval': {'lower': 90.0, 'upper': 110.0},
            'model_version': 'test_v1'
        }
        
        payload = {
            "features": {"feature1": 1.0, "feature2": 2.0},
            "model_version": "latest"
        }
        
        with patch('src.api.main.verify_token', return_value="valid_token"):
            response = client.post("/predict", json=payload, headers={"Authorization": "Bearer test_token"})
        
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "model_version" in data
        assert "timestamp" in data
    
    def test_predict_endpoint_invalid_features(self, client):
        """Test prediction with invalid features"""
        payload = {"features": {}}
        
        with patch('src.api.main.verify_token', return_value="valid_token"):
            response = client.post("/predict", json=payload, headers={"Authorization": "Bearer test_token"})
        
        assert response.status_code == 422  # Validation error
    
    def test_batch_predict_endpoint(self, client, mock_model_manager):
        """Test batch prediction endpoint"""
        mock_model_manager.predict.return_value = {
            'prediction': 100.0,
            'confidence_interval': {'lower': 90.0, 'upper': 110.0},
            'model_version': 'test_v1'
        }
        
        payload = [
            {"features": {"feature1": 1.0, "feature2": 2.0}},
            {"features": {"feature1": 2.0, "feature2": 3.0}}
        ]
        
        with patch('src.api.main.verify_token', return_value="valid_token"):
            response = client.post("/batch_predict", json=payload, headers={"Authorization": "Bearer test_token"})
        
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) == 2
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200

class TestDriftDetection:
    """Test drift detection and monitoring"""
    
    @pytest.fixture
    def reference_data(self):
        np.random.seed(42)
        return pd.DataFrame({
            'feature1': np.random.normal(0, 1, 1000),
            'feature2': np.random.choice(['A', 'B', 'C'], 1000),
            'feature3': np.random.uniform(0, 10, 1000)
        })
    
    @pytest.fixture
    def current_data_no_drift(self):
        np.random.seed(43)
        return pd.DataFrame({
            'feature1': np.random.normal(0, 1, 500),
            'feature2': np.random.choice(['A', 'B', 'C'], 500),
            'feature3': np.random.uniform(0, 10, 500)
        })
    
    @pytest.fixture
    def current_data_with_drift(self):
        np.random.seed(44)
        return pd.DataFrame({
            'feature1': np.random.normal(2, 1, 500),  # Mean shift
            'feature2': np.random.choice(['A', 'B', 'C', 'D'], 500),  # New category
            'feature3': np.random.uniform(5, 15, 500)  # Range shift
        })
    
    def test_drift_detector_initialization(self, reference_data):
        """Test drift detector initialization"""
        detector = DriftDetector(reference_data, threshold=0.1)
        assert detector.reference_data.equals(reference_data)
        assert detector.threshold == 0.1
        assert detector.feature_stats is not None
    
    def test_no_drift_detection(self, reference_data, current_data_no_drift):
        """Test no drift scenario"""
        detector = DriftDetector(reference_data, threshold=0.1)
        results = detector.detect_drift(current_data_no_drift)
        
        assert 'overall_drift' in results
        assert 'drift_score' in results
        assert 'feature_drift' in results
        # Should not detect significant drift
        assert results['drift_score'] < 0.3
    
    def test_drift_detection(self, reference_data, current_data_with_drift):
        """Test drift detection scenario"""
        detector = DriftDetector(reference_data, threshold=0.1)
        results = detector.detect_drift(current_data_with_drift)
        
        assert 'overall_drift' in results
        assert 'drift_score' in results
        assert 'feature_drift' in results
        # Should detect drift
        assert results['drift_score'] > 0.1
    
    def test_numerical_drift_detection(self, reference_data):
        """Test numerical feature drift detection"""
        detector = DriftDetector(reference_data, threshold=0.1)
        
        # Create drifted numerical data
        drifted_series = pd.Series(np.random.normal(2, 1, 500))  # Mean shift
        reference_series = reference_data['feature1']
        
        result = detector._test_numerical_drift('feature1', reference_series, drifted_series)
        
        assert 'drift_detected' in result
        assert 'drift_score' in result
        assert 'ks_statistic' in result
        assert 'psi_score' in result
    
    def test_categorical_drift_detection(self, reference_data):
        """Test categorical feature drift detection"""
        detector = DriftDetector(reference_data, threshold=0.1)
        
        # Create drifted categorical data
        drifted_series = pd.Series(np.random.choice(['A', 'B', 'C', 'D'], 500))  # New category
        reference_series = reference_data['feature2']
        
        result = detector._test_categorical_drift('feature2', reference_series, drifted_series)
        
        assert 'drift_detected' in result
        assert 'drift_score' in result
        assert 'chi2_statistic' in result
        assert 'psi_score' in result

class TestModelPerformanceMonitor:
    """Test model performance monitoring"""
    
    @pytest.fixture
    def mock_model(self):
        model = Mock()
        model.predict.return_value = np.array([1, 2, 3, 4, 5])
        return model
    
    @pytest.fixture
    def sample_performance_data(self):
        X = pd.DataFrame({'feature1': [1, 2, 3, 4, 5]})
        y = pd.Series([1.1, 2.1, 2.9, 4.1, 4.9])
        return X, y
    
    def test_performance_monitor_initialization(self, mock_model):
        """Test performance monitor initialization"""
        reference_performance = {'rmse': 0.1, 'mae': 0.08}
        monitor = ModelPerformanceMonitor(mock_model, reference_performance)
        
        assert monitor.model == mock_model
        assert monitor.reference_performance == reference_performance
    
    def test_performance_evaluation(self, mock_model, sample_performance_data):
        """Test performance evaluation"""
        X, y = sample_performance_data
        reference_performance = {'rmse': 0.1, 'mae': 0.08, 'mape': 5.0}
        
        monitor = ModelPerformanceMonitor(mock_model, reference_performance)
        results = monitor.evaluate_performance(X, y)
        
        assert 'current_metrics' in results
        assert 'reference_metrics' in results
        assert 'degradation' in results
        assert 'timestamp' in results

# Integration Tests
class TestIntegration:
    """Integration tests for the complete pipeline"""
    
    def test_end_to_end_pipeline(self):
        """Test complete pipeline from data to prediction"""
        # This would be a comprehensive test that:
        # 1. Loads sample data
        # 2. Runs feature engineering
        # 3. Trains a model
        # 4. Makes predictions
        # 5. Monitors for drift
        
        # For now, just test that all components can be imported
        from src.data.kaggle_ingestion import KaggleDataIngestion
        from src.features.feature_engineering import FeaturePipeline
        from src.training.train_model import ModelTrainer
        from src.api.main import app
        from src.monitoring.drift_detection import DriftDetector
        
        assert True  # All imports successful

if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ])