"""
File management service for ddoc (add command implementation)
"""
import shutil
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
from rich import print


class FileService:
    """Service for managing file operations (add command)"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.data_dir = self.project_root / "data"
        self.code_dir = self.project_root / "code"
        self.notebooks_dir = self.project_root / "notebooks"
    
    def add_data(self, source: str, auto_dvc: bool = True, auto_git: bool = True) -> Dict[str, Any]:
        """
        Add data file or directory to data/
        
        Args:
            source: Source file or directory path
            auto_dvc: Automatically run dvc add after copying
            
        Returns:
            Result dictionary with added files info
        """
        try:
            source_path = Path(source).resolve()
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source path does not exist: {source}"
                }
            
            # Ensure data directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            added_items = []
            
            # Handle zip files
            if source_path.is_file() and source_path.suffix == '.zip':
                extracted_dir = self._extract_zip(source_path, self.data_dir)
                added_items.append(str(extracted_dir.relative_to(self.project_root)))
            
            # Handle tar.gz files
            elif source_path.is_file() and (source_path.suffix in ['.gz', '.tar'] or '.tar.gz' in source_path.name):
                extracted_dir = self._extract_tar(source_path, self.data_dir)
                added_items.append(str(extracted_dir.relative_to(self.project_root)))
            
            # Handle directories
            elif source_path.is_dir():
                dest_dir = self.data_dir / source_path.name
                if dest_dir.exists():
                    # Merge/update directory
                    shutil.copytree(source_path, dest_dir, dirs_exist_ok=True)
                else:
                    # Copy new directory
                    shutil.copytree(source_path, dest_dir)
                added_items.append(str(dest_dir.relative_to(self.project_root)))
            
            # Handle regular files
            elif source_path.is_file():
                dest_file = self.data_dir / source_path.name
                shutil.copy2(source_path, dest_file)
                added_items.append(str(dest_file.relative_to(self.project_root)))
            
            result = {
                "success": True,
                "added_items": added_items,
                "target_directory": str(self.data_dir.relative_to(self.project_root))
            }
            
            # Automatically run dvc add
            if auto_dvc:
                dvc_result = self._dvc_add_data()
                result["dvc_tracked"] = dvc_result["success"]
                if not dvc_result["success"]:
                    result["dvc_warning"] = dvc_result.get("error", "DVC add failed")
                
                # Also git add the data.dvc file (skipped when auto_git
                # is False or there's no .git/ — Round-9).
                if dvc_result["success"] and auto_git:
                    git_result = self._git_add_dvc_file()
                    result["git_staged"] = git_result["success"]
                    if not git_result["success"]:
                        result["git_warning"] = git_result.get("error", "git add failed")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add data: {str(e)}"
            }
    
    def add_code(self, source: str, auto_git: bool = True, trainer: Optional[str] = None) -> Dict[str, Any]:
        """
        Add code file to code/
        
        Args:
            source: Source code file path
            auto_git: Automatically run git add after copying
            trainer: Optional trainer name to organize code under code/trainers/{trainer}
            
        Returns:
            Result dictionary
        """
        try:
            source_path = Path(source).resolve()
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source path does not exist: {source}"
                }
            
            if not source_path.is_file():
                return {
                    "success": False,
                    "error": f"Source must be a file: {source}"
                }
            
            # Determine target directory
            if trainer:
                dest_dir = self.code_dir / "trainers" / trainer
            else:
                dest_dir = self.code_dir
            
            # Ensure target directory exists
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file to target directory
            dest_file = dest_dir / source_path.name
            shutil.copy2(source_path, dest_file)
            
            result = {
                "success": True,
                "added_file": str(dest_file.relative_to(self.project_root)),
                "target_directory": str(dest_dir.relative_to(self.project_root))
            }
            
            # Automatically git add
            if auto_git:
                git_result = self._git_add_file(dest_file)
                result["git_staged"] = git_result["success"]
                if not git_result["success"]:
                    result["git_warning"] = git_result.get("error", "Git add failed")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add code: {str(e)}"
            }
    
    def add_notebook(self, source: str, auto_git: bool = True) -> Dict[str, Any]:
        """
        Add notebook file to notebooks/
        
        Args:
            source: Source notebook file path
            auto_git: Automatically run git add after copying
            
        Returns:
            Result dictionary
        """
        try:
            source_path = Path(source).resolve()
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source path does not exist: {source}"
                }
            
            if not source_path.is_file():
                return {
                    "success": False,
                    "error": f"Source must be a file: {source}"
                }
            
            # Ensure notebooks directory exists
            self.notebooks_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file to notebooks directory
            dest_file = self.notebooks_dir / source_path.name
            shutil.copy2(source_path, dest_file)
            
            result = {
                "success": True,
                "added_file": str(dest_file.relative_to(self.project_root)),
                "target_directory": str(self.notebooks_dir.relative_to(self.project_root))
            }
            
            # Automatically git add
            if auto_git:
                git_result = self._git_add_file(dest_file)
                result["git_staged"] = git_result["success"]
                if not git_result["success"]:
                    result["git_warning"] = git_result.get("error", "Git add failed")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add notebook: {str(e)}"
            }
    
    def _extract_zip(self, zip_path: Path, target_dir: Path) -> Path:
        """
        Extract zip file to target directory.
        
        Handles nested single-folder archives by flattening them:
        - If archive contains only one folder with same name, move contents up one level
        - Example: yolo_reference.zip containing yolo_reference/ → data/yolo_reference/
        """
        # Create extraction directory based on zip name
        extract_dir = target_dir / zip_path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Remove macOS metadata folder if present
        macosx_dir = extract_dir / "__MACOSX"
        if macosx_dir.exists():
            shutil.rmtree(macosx_dir)
        
        # Check for nested single folder with same name
        self._flatten_single_folder(extract_dir, zip_path.stem)
        
        return extract_dir
    
    def _flatten_single_folder(self, extract_dir: Path, expected_name: str) -> None:
        """
        Flatten single nested folder if it matches the expected name.
        
        Example:
            Before: data/yolo_reference/yolo_reference/train/
            After:  data/yolo_reference/train/
        
        Args:
            extract_dir: Directory where archive was extracted
            expected_name: Expected folder name (usually same as archive stem)
        """
        # Get list of items in extract directory (excluding hidden files)
        items = [item for item in extract_dir.iterdir() if not item.name.startswith('.')]
        
        # Check if there's exactly one item and it's a directory with matching name
        if len(items) == 1 and items[0].is_dir() and items[0].name == expected_name:
            nested_folder = items[0]
            
            # Move all contents from nested folder to parent
            # Use a temporary directory to avoid conflicts
            temp_dir = extract_dir.parent / f"_temp_{expected_name}"
            nested_folder.rename(temp_dir)
            
            # Move all items from temp to extract_dir
            for item in temp_dir.iterdir():
                dest = extract_dir / item.name
                # If dest exists, remove it first (shouldn't happen in normal cases)
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                item.rename(dest)
            
            # Remove the now-empty temp directory
            temp_dir.rmdir()
    
    def _extract_tar(self, tar_path: Path, target_dir: Path) -> Path:
        """
        Extract tar/tar.gz file to target directory.
        
        Handles nested single-folder archives by flattening them.
        """
        # Create extraction directory based on tar name
        if tar_path.name.endswith('.tar.gz'):
            extract_name = tar_path.name.replace('.tar.gz', '')
        elif tar_path.name.endswith('.tar'):
            extract_name = tar_path.stem
        else:
            extract_name = tar_path.stem
        
        extract_dir = target_dir / extract_name
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar_ref:
            tar_ref.extractall(extract_dir)
        
        # Remove macOS metadata folder if present
        macosx_dir = extract_dir / "__MACOSX"
        if macosx_dir.exists():
            shutil.rmtree(macosx_dir)
        
        # Check for nested single folder with same name
        self._flatten_single_folder(extract_dir, extract_name)
        
        return extract_dir
    
    def _dvc_add_data(self) -> Dict[str, Any]:
        """Run dvc add on data/ directory"""
        try:
            result = subprocess.run(
                ["dvc", "add", "data/"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "message": "Data tracked by DVC"
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"DVC add failed: {e.stderr}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "DVC not found. Please install dvc: pip install dvc"
            }
    
    def _git_add_dvc_file(self) -> Dict[str, Any]:
        """Run git add on data.dvc file"""
        try:
            dvc_file = self.project_root / "data.dvc"
            if not dvc_file.exists():
                return {
                    "success": False,
                    "error": "data.dvc file not found"
                }
            
            result = subprocess.run(
                ["git", "add", "data.dvc"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "message": "data.dvc staged in git"
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git add failed: {e.stderr}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Git not found"
            }
    
    def _git_add_file(self, file_path: Path) -> Dict[str, Any]:
        """Run git add on a specific file"""
        try:
            relative_path = file_path.relative_to(self.project_root)
            
            result = subprocess.run(
                ["git", "add", str(relative_path)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "message": f"{relative_path} staged in git"
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git add failed: {e.stderr}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Git not found"
            }
    
    def list_data_contents(self) -> Dict[str, Any]:
        """List contents of data/ directory"""
        try:
            if not self.data_dir.exists():
                return {
                    "success": True,
                    "contents": [],
                    "message": "Data directory is empty"
                }
            
            contents = []
            for item in self.data_dir.iterdir():
                if item.name.startswith('.'):
                    continue
                
                item_info = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item.relative_to(self.project_root))
                }
                
                if item.is_dir():
                    # Count files in directory
                    file_count = sum(1 for _ in item.rglob('*') if _.is_file())
                    item_info["file_count"] = file_count
                
                contents.append(item_info)
            
            return {
                "success": True,
                "contents": contents
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list data contents: {str(e)}"
            }


def get_file_service(project_root: Optional[str] = None) -> FileService:
    """Factory function to get file service instance"""
    return FileService(project_root)

