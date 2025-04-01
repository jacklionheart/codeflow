"""
Git integration for loopflow.

This module provides functionality for auto-checkpointing loopflow operations
and managing the history of generated files.
"""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from loopflow.compose.prompt import Prompt

logger = logging.getLogger(__name__)

class GitError(Exception):
    """Exception raised for git-related errors."""
    pass

LOOPFLOW_CHECKPOINT_PREFIX = "[loopflow-checkpoint]"

def is_git_repo(path: Path) -> bool:
    """
    Check if the given path is inside a git repository.
    
    Args:
        path: Directory path to check
        
    Returns:
        True if path is inside a git repository, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except Exception as e:
        logger.debug(f"Error checking git repo: {e}")
        return False

def get_current_branch(path: Path) -> Optional[str]:
    """
    Get the current git branch for the given path.
    
    Args:
        path: Directory path to check
        
    Returns:
        Current branch name or None if not in a repo or on a detached HEAD
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        branch = result.stdout.strip()
        return branch if branch != "HEAD" else None
    except subprocess.CalledProcessError as e:
        logger.debug(f"Error getting current branch: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error getting branch: {e}")
        return None

def stage_all_files(path: Path) -> bool:
    """
    Add all changed files to git staging.
    
    Args:
        path: Directory path to stage files from
        
    Returns:
        True if successful, False otherwise
    """
    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=path,
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to stage files: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error staging files: {e}")
        return False

def create_checkpoint(
    path: Path, 
    command: str, 
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Create a loopflow checkpoint commit.
    
    Args:
        path: Directory path for the repository
        command: The loopflow command that was run
        details: Optional details to include in the commit message
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Construct commit message
        commit_message = f"{LOOPFLOW_CHECKPOINT_PREFIX} {command}"
        if details:
            # Add relevant details (files processed, etc.)
            detail_str = ", ".join(f"{k}: {v}" for k, v in details.items())
            commit_message += f" ({detail_str})"
        
        # Create commit
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=path,
            capture_output=True,
            check=True
        )
        logger.info(f"Created checkpoint: {commit_message}")
        return True
    except subprocess.CalledProcessError as e:
        # If nothing to commit, that's not an error
        if "nothing to commit" in e.stderr:
            logger.info("No changes to checkpoint")
            return True
        logger.warning(f"Failed to create checkpoint: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error creating checkpoint: {e}")
        return False

def find_last_non_loopflow_commit(path: Path) -> Optional[str]:
    """
    Find the last git commit that wasn't an auto-generated loopflow checkpoint.
    
    Args:
        path: Directory path for the repository
        
    Returns:
        Commit hash of the last non-loopflow commit, or None if not found
    """
    try:
        # Get commit history with messages
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H|%s"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse commit history
        for line in result.stdout.splitlines():
            parts = line.split('|', 1)
            if len(parts) < 2:
                continue
                
            commit_hash, message = parts
            if not message.startswith(LOOPFLOW_CHECKPOINT_PREFIX):
                return commit_hash
                
        return None
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to find last non-loopflow commit: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error finding commit: {e}")
        return None

def rebase_to_commit(path: Path, commit_hash: str) -> bool:
    """
    Rebase to the specified commit, preserving working tree changes.
    
    Args:
        path: Directory path for the repository
        commit_hash: Hash of the commit to rebase to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # First stash any uncommitted changes
        subprocess.run(
            ["git", "stash"],
            cwd=path,
            capture_output=True,
            check=True
        )
        
        # Perform the rebase
        subprocess.run(
            ["git", "reset", "--soft", commit_hash],
            cwd=path,
            capture_output=True,
            check=True
        )
        
        # Apply stashed changes if any were stashed
        stash_result = subprocess.run(
            ["git", "stash", "list"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        
        if stash_result.stdout.strip():
            subprocess.run(
                ["git", "stash", "pop"],
                cwd=path,
                capture_output=True,
                check=True
            )
            
        logger.info(f"Successfully rebased to commit {commit_hash}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to rebase: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during rebase: {e}")
        return False

def should_auto_checkpoint(path: Path) -> bool:
    """
    Determine if auto-checkpointing should be enabled for this project/command.
    
    Args:
        path: The project directory
        config: The loopflow configuration
        
    Returns:
        True if auto-checkpointing should be enabled
    """
    # Check if we're in a git repository
    if not is_git_repo(path):
        return False
        
    # Get current branch
    branch = get_current_branch(path)
    if not branch:
        return False
    
    if branch == "main":
        return False
    
    return True

def auto_checkpoint(
    path: Path, 
    command: str, 
    prompt: Prompt
) -> bool:
    """
    Perform an auto-checkpoint if conditions are met.
    
    Args:
        path: The project directory
        command: The loopflow command being run
        config: The loopflow configuration
        details: Optional details for the commit message
        
    Returns:
        True if checkpoint was created or not needed, False if failed
    """
    if not should_auto_checkpoint(path):
        logger.debug("Auto-checkpointing not enabled or applicable")
        return True
        
    # Stage all files
    if not stage_all_files(path):
        logger.warning("Failed to stage files for checkpoint")
        return False

    details = {
        "path": path,
        "goal": prompt.goal,
        "output_files": prompt.output_files
    }

    # Create the checkpoint
    return create_checkpoint(path, command, details)