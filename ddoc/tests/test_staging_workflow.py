"""
Test staging workflow for dataset commands
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from ddoc.core.staging_service import get_staging_service
from ddoc.core.dataset_service import get_dataset_service


def test_staging_service_basic():
    """Test basic staging service operations"""
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        staging_service = get_staging_service(tmpdir)
        
        # Test staging a new dataset
        result = staging_service.stage_dataset(
            name="test_data",
            path="/tmp/test_data",
            operation="new",
            formats=[".jpg"],
            current_hash="abc123"
        )
        
        assert result['success'] == True
        assert result['dataset'] == "test_data"
        
        # Test is_staged
        assert staging_service.is_staged("test_data") == True
        assert staging_service.is_staged("non_existent") == False
        
        # Test get_staged_changes
        staged = staging_service.get_staged_changes()
        assert staged['success'] == True
        assert len(staged['new']) == 1
        assert staged['new'][0]['name'] == "test_data"
        
        # Test unstaging
        result = staging_service.unstage_dataset("test_data")
        assert result['success'] == True
        assert staging_service.is_staged("test_data") == False
        
        # Test clear staging
        staging_service.stage_dataset("test1", "/tmp/test1", "new")
        staging_service.stage_dataset("test2", "/tmp/test2", "new")
        
        result = staging_service.clear_staging()
        assert result['success'] == True
        
        staged = staging_service.get_staged_changes()
        assert staged['total'] == 0


def test_staging_modified_dataset():
    """Test staging modified datasets"""
    with tempfile.TemporaryDirectory() as tmpdir:
        staging_service = get_staging_service(tmpdir)
        
        # Stage modified dataset
        result = staging_service.stage_dataset(
            name="existing_data",
            path="/tmp/existing_data",
            operation="modified",
            current_hash="def456"
        )
        
        assert result['success'] == True
        
        # Check staged changes
        staged = staging_service.get_staged_changes()
        assert len(staged['modified']) == 1
        assert staged['modified'][0]['name'] == "existing_data"


def test_get_staged_dataset():
    """Test retrieving specific staged dataset info"""
    with tempfile.TemporaryDirectory() as tmpdir:
        staging_service = get_staging_service(tmpdir)
        
        staging_service.stage_dataset(
            name="test_data",
            path="/tmp/test_data",
            operation="new",
            formats=[".jpg", ".png"],
            config="config.yaml",
            current_hash="abc123",
            metadata={"custom": "value"}
        )
        
        info = staging_service.get_staged_dataset("test_data")
        assert info is not None
        assert info['operation'] == "new"
        assert info['path'] == "/tmp/test_data"
        assert info['current_hash'] == "abc123"
        assert info['metadata']['custom'] == "value"
        
        # Non-existent dataset
        info = staging_service.get_staged_dataset("non_existent")
        assert info is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

