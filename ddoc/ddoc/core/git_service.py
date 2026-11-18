"""
Git integration service for ddoc
"""
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from rich import print


class GitService:
    """Service for git operations"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        git_dir = self.project_root / ".git"
        return git_dir.exists()
    
    def get_current_commit(self) -> Optional[str]:
        """
        Get current git commit hash
        
        Returns:
            Commit hash or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    def get_current_branch(self) -> Optional[str]:
        """
        Get current git branch name
        
        Returns:
            Branch name or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get git status information
        
        Returns:
            Dictionary with status information
        """
        try:
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            has_changes = len(result.stdout.strip()) > 0
            changes = result.stdout.strip().split('\n') if has_changes else []
            
            # Get current branch and commit
            branch = self.get_current_branch()
            commit = self.get_current_commit()
            
            return {
                "success": True,
                "has_uncommitted_changes": has_changes,
                "changes": changes,
                "current_branch": branch,
                "current_commit": commit,
                "commit_short": commit[:7] if commit else None
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git status failed: {e.stderr}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Git not found"
            }
    
    def checkout(self, revision: str, force: bool = False, ignore_ddoc: bool = True) -> Dict[str, Any]:
        """
        Checkout a specific git revision
        
        Args:
            revision: Commit hash or branch name
            force: Force checkout even with uncommitted changes
            ignore_ddoc: Ignore .ddoc directory changes when checking for uncommitted changes
            
        Returns:
            Result dictionary
        """
        try:
            # Check for uncommitted changes first
            if not force:
                status = self.get_status()
                if status.get("has_uncommitted_changes"):
                    # Filter out .ddoc directory changes if requested
                    if ignore_ddoc:
                        changes = status.get("changes", [])
                        relevant_changes = []
                        for change in changes:
                            # Extract file path (after status characters and space)
                            # Format: "XY path" or "?? path" for untracked
                            parts = change.strip().split(None, 1)
                            if len(parts) >= 2:
                                file_path = parts[1]
                                # Ignore .ddoc directory changes
                                if not file_path.startswith(".ddoc/"):
                                    relevant_changes.append(change)
                            else:
                                # If format is unexpected, include it to be safe
                                relevant_changes.append(change)
                        
                        if relevant_changes:
                            return {
                                "success": False,
                                "error": "You have uncommitted changes. Commit or stash them first, or use --force."
                            }
                    else:
                        # Don't ignore .ddoc, return error if any changes exist
                        return {
                            "success": False,
                            "error": "You have uncommitted changes. Commit or stash them first, or use --force."
                        }
            
            # If ignoring .ddoc and there are .ddoc changes, stash them temporarily
            ddoc_stashed = False
            if ignore_ddoc and not force:
                status = self.get_status()
                if status.get("has_uncommitted_changes"):
                    changes = status.get("changes", [])
                    # Check if there are any .ddoc changes
                    has_ddoc_changes = any(
                        len(c.strip().split(None, 1)) >= 2 and 
                        c.strip().split(None, 1)[1].startswith(".ddoc/")
                        for c in changes
                    )
                    
                    if has_ddoc_changes:
                        # Stash all changes (we'll restore them after checkout)
                        try:
                            stash_result = subprocess.run(
                                ["git", "stash", "push", "-m", "ddoc-temp-stash-before-checkout"],
                                cwd=self.project_root,
                                capture_output=True,
                                text=True,
                                check=True
                            )
                            ddoc_stashed = True
                        except subprocess.CalledProcessError:
                            # If stash fails, try to proceed with force
                            pass
            
            # Checkout the revision
            cmd = ["git", "checkout", revision]
            if force or ddoc_stashed:
                cmd.append("--force")
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Restore stashed changes if they were stashed
            if ddoc_stashed:
                try:
                    # Find the stash we created
                    stash_list_result = subprocess.run(
                        ["git", "stash", "list"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Look for our stash
                    stash_lines = stash_list_result.stdout.strip().split('\n')
                    for line in stash_lines:
                        if "ddoc-temp-stash-before-checkout" in line:
                            # Extract stash index (format: "stash@{0}: ...")
                            stash_index = line.split(':')[0].split('{')[1].split('}')[0]
                            # Apply the stash
                            stash_apply_result = subprocess.run(
                                ["git", "stash", "apply", f"stash@{{{stash_index}}}"],
                                cwd=self.project_root,
                                capture_output=True,
                                text=True,
                                check=False  # Don't fail if apply fails
                            )
                            # Drop the stash after applying
                            subprocess.run(
                                ["git", "stash", "drop", f"stash@{{{stash_index}}}"],
                                cwd=self.project_root,
                                capture_output=True,
                                text=True,
                                check=False
                            )
                            break
                except Exception:
                    # If restore fails, continue anyway
                    pass
            
            return {
                "success": True,
                "revision": revision,
                "message": result.stdout.strip()
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git checkout failed: {e.stderr}"
            }
    
    def add(self, paths: List[str]) -> Dict[str, Any]:
        """
        Add files to git staging area
        
        Args:
            paths: List of file paths to add
            
        Returns:
            Result dictionary
        """
        try:
            result = subprocess.run(
                ["git", "add"] + paths,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "added_files": paths
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git add failed: {e.stderr}"
            }
    
    def add_all(self) -> Dict[str, Any]:
        """
        Add all changes to git staging area (git add -A)
        
        Returns:
            Result dictionary
        """
        try:
            result = subprocess.run(
                ["git", "add", "-A"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "message": "All changes staged"
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git add failed: {e.stderr}"
            }
    
    def commit(self, message: str, allow_empty: bool = False) -> Dict[str, Any]:
        """
        Create a git commit
        
        Args:
            message: Commit message
            allow_empty: Allow empty commits
            
        Returns:
            Result dictionary with commit hash
        """
        try:
            cmd = ["git", "commit", "-m", message]
            if allow_empty:
                cmd.append("--allow-empty")
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get the new commit hash
            commit_hash = self.get_current_commit()
            
            return {
                "success": True,
                "commit_hash": commit_hash,
                "commit_short": commit_hash[:7] if commit_hash else None,
                "message": message
            }
            
        except subprocess.CalledProcessError as e:
            # ``git commit`` writes "nothing to commit" to stdout, not
            # stderr, and exits non-zero. The previous implementation only
            # captured stderr, so callers saw an empty error string and
            # fell into the generic failure branch — breaking the typical
            # ``ddoc snapshot create`` flow on a clean tree. Treat the
            # nothing-to-commit case as a benign skip; surface the
            # combined output otherwise.
            combined = f"{e.stdout or ''}\n{e.stderr or ''}".strip()
            if "nothing to commit" in (e.stdout or "").lower() or \
               "nothing to commit" in (e.stderr or "").lower():
                return {
                    "success": True,
                    "skipped": True,
                    "message": "Nothing to commit",
                    "commit_hash": self.get_current_commit(),
                }
            return {
                "success": False,
                "error": f"Git commit failed: {combined}",
            }

    def diff(self, commit1: str, commit2: str, paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get diff between two commits
        
        Args:
            commit1: First commit hash
            commit2: Second commit hash
            paths: Optional list of paths to diff
            
        Returns:
            Result dictionary with diff output
        """
        try:
            cmd = ["git", "diff", commit1, commit2]
            if paths:
                cmd.append("--")
                cmd.extend(paths)
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get file stats
            stat_result = subprocess.run(
                ["git", "diff", "--stat", commit1, commit2],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "success": True,
                "diff": result.stdout,
                "stat": stat_result.stdout,
                "has_changes": len(result.stdout) > 0
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git diff failed: {e.stderr}"
            }
    
    def log(self, max_count: Optional[int] = None, oneline: bool = False) -> Dict[str, Any]:
        """
        Get git log
        
        Args:
            max_count: Maximum number of commits to show
            oneline: Use oneline format
            
        Returns:
            Result dictionary with log entries
        """
        try:
            cmd = ["git", "log"]
            
            if oneline:
                cmd.append("--oneline")
            else:
                cmd.extend(["--pretty=format:%H|%h|%an|%ae|%ad|%s", "--date=iso"])
            
            if max_count:
                cmd.extend(["-n", str(max_count)])
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            if oneline:
                entries = [line for line in result.stdout.strip().split('\n') if line]
            else:
                entries = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) == 6:
                            entries.append({
                                "hash": parts[0],
                                "short_hash": parts[1],
                                "author": parts[2],
                                "email": parts[3],
                                "date": parts[4],
                                "message": parts[5]
                            })
            
            return {
                "success": True,
                "entries": entries,
                "count": len(entries)
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git log failed: {e.stderr}"
            }
    
    def get_commit_info(self, commit_hash: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific commit
        
        Args:
            commit_hash: Commit hash to query
            
        Returns:
            Dictionary with commit information
        """
        try:
            result = subprocess.run(
                ["git", "show", "--quiet", "--pretty=format:%H|%h|%an|%ae|%ad|%s", "--date=iso", commit_hash],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            parts = result.stdout.strip().split('|')
            if len(parts) == 6:
                return {
                    "success": True,
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author": parts[2],
                    "email": parts[3],
                    "date": parts[4],
                    "message": parts[5]
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to parse commit info"
                }
                
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to get commit info: {e.stderr}"
            }


def get_git_service(project_root: Optional[str] = None) -> GitService:
    """Factory function to get git service instance"""
    return GitService(project_root)

