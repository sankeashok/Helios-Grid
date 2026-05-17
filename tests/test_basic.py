"""
Simple test configuration for CI/CD pipeline
Tests basic functionality without requiring Azure dependencies
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest


class TestBasicFunctionality:
    """Test basic Python functionality and imports"""

    def test_python_version(self):
        """Test that Python version is compatible"""
        assert sys.version_info >= (3, 8)

    def test_numpy_functionality(self):
        """Test numpy basic operations"""
        arr = np.array([1, 2, 3, 4, 5])
        assert arr.mean() == 3.0
        assert arr.sum() == 15

    def test_pandas_functionality(self):
        """Test pandas basic operations"""
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        assert len(df) == 3
        assert df["A"].sum() == 6

    def test_json_operations(self):
        """Test JSON serialization/deserialization"""
        data = {"test": "value", "number": 42}
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed == data

    def test_file_operations(self):
        """Test basic file operations"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            with open(temp_path, "r") as f:
                content = f.read()
            assert content == "test content"
        finally:
            os.unlink(temp_path)


class TestMockingCapabilities:
    """Test mocking capabilities for CI/CD"""

    def test_mock_creation(self):
        """Test that mocking works correctly"""
        mock_obj = Mock()
        mock_obj.method.return_value = "mocked"
        assert mock_obj.method() == "mocked"

    def test_patch_functionality(self):
        """Test patching functionality"""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            assert os.path.exists("fake_path") is True

    def test_magic_mock(self):
        """Test MagicMock functionality"""
        magic_mock = MagicMock()
        magic_mock.__len__.return_value = 5
        assert len(magic_mock) == 5


class TestDataProcessing:
    """Test data processing capabilities"""

    def test_dataframe_creation(self):
        """Test DataFrame creation and manipulation"""
        # Create sample energy consumption data
        data = {
            "timestamp": pd.date_range("2023-01-01", periods=24, freq="h"),
            "energy_consumption": np.random.normal(100, 20, 24),
            "temperature": np.random.normal(20, 5, 24),
        }
        df = pd.DataFrame(data)

        assert len(df) == 24
        assert "timestamp" in df.columns
        assert "energy_consumption" in df.columns
        assert df["energy_consumption"].dtype in [np.float64, np.float32]

    def test_time_series_operations(self):
        """Test time series operations"""
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        ts = pd.Series(range(10), index=dates)

        # Test resampling with explicit frequency
        try:
            monthly = ts.resample("ME").sum()  # Month End frequency
            assert len(monthly) >= 1
        except Exception:
            # Fallback for older pandas versions
            monthly = ts.resample("M").sum()
            assert len(monthly) >= 1

        # Test rolling operations
        rolling_mean = ts.rolling(window=3).mean()
        assert len(rolling_mean) == 10

    def test_feature_engineering_basics(self):
        """Test basic feature engineering operations"""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2023-01-01", periods=48, freq="h"),
                "value": range(48),
            }
        )

        # Add time-based features
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek

        assert "hour" in df.columns
        assert "day_of_week" in df.columns
        assert df["hour"].min() >= 0
        assert df["hour"].max() <= 23


class TestMLBasics:
    """Test basic ML functionality without complex dependencies"""

    def test_sklearn_imports(self):
        """Test that sklearn can be imported"""
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.linear_model import LinearRegression
            from sklearn.metrics import mean_squared_error

            # Create simple model
            model = LinearRegression()
            X = np.array([[1], [2], [3], [4]])
            y = np.array([2, 4, 6, 8])
            model.fit(X, y)

            predictions = model.predict([[5]])
            assert len(predictions) == 1
            assert abs(predictions[0] - 10) < 0.1  # Should predict ~10

        except ImportError as e:
            pytest.skip(f"Sklearn not available: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error in sklearn test: {e}")

    def test_model_serialization(self):
        """Test model serialization with joblib"""
        try:
            import joblib
            from sklearn.linear_model import LinearRegression

            model = LinearRegression()
            X = np.array([[1], [2], [3]])
            y = np.array([2, 4, 6])
            model.fit(X, y)

            # Test serialization using a regular file
            import tempfile

            temp_dir = tempfile.mkdtemp()
            model_path = os.path.join(temp_dir, "test_model.pkl")

            try:
                joblib.dump(model, model_path)
                loaded_model = joblib.load(model_path)

                # Test that loaded model works
                pred_original = model.predict([[4]])
                pred_loaded = loaded_model.predict([[4]])
                np.testing.assert_array_almost_equal(pred_original, pred_loaded)
            finally:
                # Clean up
                if os.path.exists(model_path):
                    os.remove(model_path)
                os.rmdir(temp_dir)

        except ImportError as e:
            pytest.skip(f"Required packages not available: {e}")


class TestConfigurationHandling:
    """Test configuration and environment handling"""

    def test_environment_variables(self):
        """Test environment variable handling"""
        test_var = "TEST_HELIOS_GRID_VAR"
        test_value = "test_value_123"

        # Set environment variable
        os.environ[test_var] = test_value
        assert os.getenv(test_var) == test_value

        # Clean up
        del os.environ[test_var]
        assert os.getenv(test_var) is None

    def test_config_file_handling(self):
        """Test configuration file handling"""
        config = {
            "model": {"type": "xgboost", "params": {"n_estimators": 100}},
            "data": {"source": "kaggle", "dataset": "energy-consumption"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            with open(config_path, "r") as f:
                loaded_config = json.load(f)
            assert loaded_config == config
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
