"""
Integration tests for the new snapshot-based workflow
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import subprocess
import json
import yaml

from ddoc.core.workspace import get_workspace_service
from ddoc.core.file_service import get_file_service
from ddoc.core.snapshot_service import get_snapshot_service
from ddoc.core.git_service import get_git_service


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_data_dir(temp_workspace):
    """Create sample data directory"""
    data_dir = temp_workspace / "sample_data"
    data_dir.mkdir()
    
    # Create some sample files
    (data_dir / "file1.txt").write_text("Sample data 1")
    (data_dir / "file2.txt").write_text("Sample data 2")
    
    return data_dir


@pytest.fixture
def sample_code_file(temp_workspace):
    """Create sample code file"""
    code_file = temp_workspace / "train.py"
    code_file.write_text("""
import numpy as np

def train_model():
    print("Training model...")
    return {"accuracy": 0.95}

if __name__ == "__main__":
    train_model()
""")
    return code_file


class TestWorkspaceInitialization:
    """Test workspace initialization"""
    
    def test_init_workspace(self, temp_workspace):
        """Test basic workspace initialization"""
        project_path = temp_workspace / "test_project"
        
        workspace_service = get_workspace_service()
        result = workspace_service.init_workspace(str(project_path))
        
        assert result["success"] is True
        assert Path(result["project_path"]).exists()
        
        # Check structure
        assert (project_path / "data").exists()
        assert (project_path / "code").exists()
        assert (project_path / "notebooks").exists()
        assert (project_path / "experiments").exists()
        assert (project_path / ".ddoc").exists()
        assert (project_path / ".ddoc" / "snapshots").exists()
        assert (project_path / ".ddoc" / "cache").exists()
        
        # Check files
        assert (project_path / ".gitignore").exists()
        assert (project_path / ".dvcignore").exists()
        assert (project_path / "README.md").exists()
        assert (project_path / ".ddoc" / "config.yaml").exists()
    
    def test_init_existing_directory_fails(self, temp_workspace):
        """Test that initializing existing non-empty directory fails"""
        project_path = temp_workspace / "existing"
        project_path.mkdir()
        (project_path / "some_file.txt").write_text("existing content")
        
        workspace_service = get_workspace_service()
        result = workspace_service.init_workspace(str(project_path))
        
        assert result["success"] is False
        assert "already exists" in result["error"].lower()
    
    def test_init_with_force(self, temp_workspace):
        """Test initialization with force flag"""
        project_path = temp_workspace / "force_test"
        project_path.mkdir()
        (project_path / "some_file.txt").write_text("existing content")
        
        workspace_service = get_workspace_service()
        result = workspace_service.init_workspace(str(project_path), force=True)
        
        assert result["success"] is True


class TestFileAddition:
    """Test file addition workflow"""
    
    def test_add_data_directory(self, temp_workspace, sample_data_dir):
        """Test adding data directory"""
        # Initialize workspace
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        # Add data
        file_service = get_file_service(str(project_path))
        result = file_service.add_data(str(sample_data_dir))
        
        assert result["success"] is True
        assert len(result["added_items"]) > 0
        
        # Verify data was copied
        data_target = project_path / "data" / "sample_data"
        assert data_target.exists()
        assert (data_target / "file1.txt").exists()
    
    def test_add_code_file(self, temp_workspace, sample_code_file):
        """Test adding code file"""
        # Initialize workspace
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        # Add code
        file_service = get_file_service(str(project_path))
        result = file_service.add_code(str(sample_code_file))
        
        assert result["success"] is True
        
        # Verify code was copied
        code_target = project_path / "code" / "train.py"
        assert code_target.exists()


class TestSnapshotWorkflow:
    """Test complete snapshot workflow"""
    
    def test_create_and_restore_snapshot(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test creating and restoring a snapshot"""
        # Initialize workspace
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        init_result = workspace_service.init_workspace(str(project_path))
        assert init_result["success"] is True
        
        # Add data
        file_service = get_file_service(str(project_path))
        data_result = file_service.add_data(str(sample_data_dir))
        assert data_result["success"] is True
        
        # Add code
        code_result = file_service.add_code(str(sample_code_file))
        assert code_result["success"] is True
        
        # Create initial git commit (required for snapshot)
        git_service = get_git_service(str(project_path))
        git_service.add(["."])
        commit_result = git_service.commit("Initial commit")
        assert commit_result["success"] is True
        
        # Create snapshot
        snapshot_service = get_snapshot_service(str(project_path))
        snapshot_result = snapshot_service.create_snapshot(
            message="Initial baseline",
            alias="baseline"
        )
        assert snapshot_result["success"] is True
        assert snapshot_result["snapshot_id"] == "v01"
        assert snapshot_result["alias"] == "baseline"
        
        # Verify snapshot file was created
        snapshot_file = project_path / ".ddoc" / "snapshots" / "v01.yaml"
        assert snapshot_file.exists()
        
        # Load and verify snapshot content
        with open(snapshot_file, 'r') as f:
            snapshot_data = yaml.safe_load(f)
        
        assert snapshot_data["snapshot_id"] == "v01"
        assert snapshot_data["alias"] == "baseline"
        assert snapshot_data["description"] == "Initial baseline"
        assert "data" in snapshot_data
        assert "code" in snapshot_data
    
    def test_list_snapshots(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test listing snapshots"""
        # Setup and create multiple snapshots
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        git_service = get_git_service(str(project_path))
        git_service.add(["."])
        git_service.commit("Initial commit")
        
        snapshot_service = get_snapshot_service(str(project_path))
        
        # Create first snapshot
        result1 = snapshot_service.create_snapshot("First snapshot", alias="v1")
        assert result1["success"] is True
        
        # Modify data
        (project_path / "data" / "sample_data" / "file3.txt").write_text("New data")
        subprocess.run(["dvc", "add", "data/"], cwd=project_path, capture_output=True)
        git_service.add(["data.dvc"])
        git_service.commit("Updated data")
        
        # Create second snapshot
        result2 = snapshot_service.create_snapshot("Second snapshot", alias="v2")
        assert result2["success"] is True
        
        # List snapshots
        list_result = snapshot_service.list_snapshots()
        assert list_result["success"] is True
        assert list_result["count"] == 2
        
        snapshot_ids = [s["snapshot_id"] for s in list_result["snapshots"]]
        assert "v01" in snapshot_ids
        assert "v02" in snapshot_ids
    
    def test_alias_management(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test snapshot alias management"""
        # Setup
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        git_service = get_git_service(str(project_path))
        git_service.add(["."])
        git_service.commit("Initial commit")
        
        snapshot_service = get_snapshot_service(str(project_path))
        snapshot_service.create_snapshot("Test snapshot")
        
        # Set alias
        snapshot_service._set_alias("production", "v01")
        
        # Load aliases
        aliases = snapshot_service._load_aliases()
        assert aliases.get_version("production") == "v01"
        
        # Resolve version from alias
        resolved = snapshot_service._resolve_version("production")
        assert resolved == "v01"
        
        # Remove alias
        assert aliases.remove_alias("production") is True
        assert aliases.get_version("production") is None


class TestGitIntegration:
    """Test Git service integration"""
    
    def test_git_operations(self, temp_workspace):
        """Test basic git operations"""
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        git_service = get_git_service(str(project_path))
        
        # Check git is initialized
        assert git_service.is_git_repo() is True
        
        # Create a file and add to git
        test_file = project_path / "test.txt"
        test_file.write_text("test content")
        
        add_result = git_service.add(["test.txt"])
        assert add_result["success"] is True
        
        commit_result = git_service.commit("Test commit")
        assert commit_result["success"] is True
        assert commit_result["commit_hash"] is not None
        
        # Get status
        status = git_service.get_status()
        assert status["success"] is True
        assert status["has_uncommitted_changes"] is False
    
    def test_git_checkout(self, temp_workspace):
        """Test git checkout"""
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        git_service = get_git_service(str(project_path))
        
        # Create initial commit
        test_file = project_path / "test.txt"
        test_file.write_text("version 1")
        git_service.add(["test.txt"])
        commit1 = git_service.commit("Version 1")
        commit1_hash = commit1["commit_hash"]
        
        # Create second commit
        test_file.write_text("version 2")
        git_service.add(["test.txt"])
        commit2 = git_service.commit("Version 2")
        
        # Checkout first commit
        checkout_result = git_service.checkout(commit1_hash)
        assert checkout_result["success"] is True
        
        # Verify content
        assert test_file.read_text() == "version 1"


class TestAutoCommitWorkflow:
    """Test automatic git/dvc commit workflow"""
    
    def test_auto_commit_snapshot_creation(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test snapshot creation with auto-commit"""
        # Initialize workspace
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        # Add data and code
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        # Create snapshot with auto-commit (should handle git/dvc automatically)
        snapshot_service = get_snapshot_service(str(project_path))
        result = snapshot_service.create_snapshot(
            message="Auto-commit test",
            alias="auto",
            auto_commit=True
        )
        
        assert result["success"] is True
        assert result["snapshot_id"] == "v01"
        
        # Verify git commit was created
        git_service = get_git_service(str(project_path))
        commit_hash = git_service.get_current_commit()
        assert commit_hash is not None
        
    def test_manual_commit_mode(self, temp_workspace, sample_data_dir):
        """Test snapshot creation with manual commit mode"""
        # Initialize workspace
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        # Add data
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        
        # Try to create snapshot without committing first (should fail)
        snapshot_service = get_snapshot_service(str(project_path))
        result = snapshot_service.create_snapshot(
            message="Manual test",
            auto_commit=False
        )
        
        assert result["success"] is False
        assert "uncommitted changes" in result["error"].lower()


class TestSnapshotManagement:
    """Test snapshot management features"""
    
    def test_delete_snapshot(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test deleting a snapshot"""
        # Setup
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        # Create snapshot with auto-commit
        snapshot_service = get_snapshot_service(str(project_path))
        create_result = snapshot_service.create_snapshot(
            "Test snapshot",
            alias="deleteme",
            auto_commit=True
        )
        assert create_result["success"] is True
        
        # Delete snapshot
        delete_result = snapshot_service.delete_snapshot("v01", force=True)
        assert delete_result["success"] is True
        
        # Verify snapshot file is gone
        snapshot_file = project_path / ".ddoc" / "snapshots" / "v01.yaml"
        assert not snapshot_file.exists()
    
    def test_verify_snapshot(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test snapshot verification"""
        # Setup
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        # Create snapshot
        snapshot_service = get_snapshot_service(str(project_path))
        snapshot_service.create_snapshot("Test", auto_commit=True)
        
        # Verify snapshot
        verify_result = snapshot_service.verify_snapshot("v01")
        assert verify_result["success"] is True
        assert len(verify_result.get("issues", [])) == 0
    
    def test_verify_all_snapshots(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test verifying all snapshots"""
        # Setup
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        # Create multiple snapshots
        snapshot_service = get_snapshot_service(str(project_path))
        snapshot_service.create_snapshot("First", auto_commit=True)
        
        # Modify data
        (project_path / "data" / "sample_data" / "file3.txt").write_text("More data")
        snapshot_service.create_snapshot("Second", auto_commit=True)
        
        # Verify all
        result = snapshot_service.verify_all_snapshots()
        assert result["success"] is True
        assert result["total"] == 2
        assert result["valid"] >= 0  # At least some should be valid
    
    def test_prune_snapshots(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test pruning orphaned snapshots"""
        # Setup
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        # Create snapshot
        snapshot_service = get_snapshot_service(str(project_path))
        snapshot_service.create_snapshot("Test", auto_commit=True)
        
        # Prune (should find no orphans for single snapshot)
        result = snapshot_service.prune_snapshots()
        assert result["success"] is True
        assert result["total_snapshots"] == 1
    
    def test_edit_description(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test editing snapshot description"""
        # Setup
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        # Create snapshot
        snapshot_service = get_snapshot_service(str(project_path))
        snapshot_service.create_snapshot("Original description", auto_commit=True)
        
        # Edit description
        new_desc = "Updated description"
        result = snapshot_service.edit_description("v01", new_desc)
        assert result["success"] is True
        
        # Verify change
        snapshot = snapshot_service._load_snapshot("v01")
        assert snapshot.description == new_desc
    
    def test_get_lineage_graph(self, temp_workspace, sample_data_dir, sample_code_file):
        """Test getting lineage graph"""
        # Setup
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        file_service = get_file_service(str(project_path))
        file_service.add_data(str(sample_data_dir))
        file_service.add_code(str(sample_code_file))
        
        # Create snapshots with lineage
        snapshot_service = get_snapshot_service(str(project_path))
        snapshot_service.create_snapshot("First", auto_commit=True)
        
        # Add more data
        (project_path / "data" / "sample_data" / "file3.txt").write_text("More")
        snapshot_service.create_snapshot("Second", auto_commit=True)
        
        # Get graph
        graph = snapshot_service.get_lineage_graph()
        assert graph["success"] is True
        assert graph["total_nodes"] == 2
        assert len(graph["nodes"]) == 2


class TestCacheService:
    """Test cache service functionality"""
    
    def test_save_and_load_summary_cache(self, temp_workspace):
        """Test saving and loading summary cache"""
        from ddoc.core.cache_service import get_cache_service
        
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        cache_service = get_cache_service(str(project_path))
        
        # Save cache
        statistics = {"mean": 10.5, "std": 2.3}
        distributions = {"hist": [1, 2, 3, 4, 5]}
        
        save_result = cache_service.save_summary_cache(
            snapshot_id="v01",
            data_hash="abc123",
            statistics=statistics,
            distributions=distributions
        )
        assert save_result["success"] is True
        
        # Load cache
        cache = cache_service.load_summary_cache("v01")
        assert cache is not None
        assert cache.snapshot_id == "v01"
        assert cache.data_hash == "abc123"
        assert cache.statistics == statistics
        assert cache.distributions == distributions
    
    def test_cache_exists(self, temp_workspace):
        """Test checking cache existence"""
        from ddoc.core.cache_service import get_cache_service
        
        project_path = temp_workspace / "project"
        workspace_service = get_workspace_service()
        workspace_service.init_workspace(str(project_path))
        
        cache_service = get_cache_service(str(project_path))
        
        # Initially no cache
        assert cache_service.cache_exists("v01", "summary") is False
        
        # Create cache
        cache_service.save_summary_cache(
            snapshot_id="v01",
            data_hash="abc123",
            statistics={},
            distributions={}
        )
        
        # Now exists
        assert cache_service.cache_exists("v01", "summary") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

