"""
Session implementation for loopflow.

The Session class provides the execution environment for workflows, handling
timeouts, resource management, and file operations. It creates and manages
the Team and User objects that the workflow uses for communication.
"""

import asyncio
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Set

from .prompt import Prompt
from .workflow import default_pipeline, Job, Context
from .llm import LLMProvider, LLM
from .team import Team

class SessionError(Exception):
    """
    Raised when session-level operations fail.
    
    Includes context about what the session was trying to do and relevant
    metrics at the time of failure for debugging and monitoring.
    """
    def __init__(self, message: str, context: Dict[str, Any]):
        self.context = context
        super().__init__(f"Session failed: {message}")

class User:
    """
    Represents the human user interacting with the session.
    """
    def __init__(self, name: str = "user"):
        self.name = name

    async def chat(self, prompt: str) -> str:
        """
        Chat with the user and return their response.
        """
        print("\n" + prompt + "\n")
        return input("Your response: ")

class Session:
    """
    Manages the execution environment for code generation pipelines.
    
    The Session handles operational concerns like timeouts and resource tracking
    so that the core workflow logic doesn't have to worry about them. It creates
    and manages the communication channels (Team and User) that the workflow
    uses to interact with models and humans.
    """
    
    def __init__(
        self,
        user: User,
        available_llms: Dict[str, LLM],
        provider: LLMProvider,
        pipeline: Job | None = None,
        timeout: float = 300.0,
    ):
        """
        Initialize session with its execution configuration.
        
        Args:
            user: The user to interact with
            provider: The LLM provider to use
            timeout: Maximum execution time in seconds
        """
        self.user = user
        self.provider = provider
        self.timeout = timeout
        self.available_llms = available_llms
        self.pipeline = pipeline or default_pipeline()

        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._temp_dir: Optional[Path] = None
        
        assert(len(self.available_llms) > 0)
    
    async def run(self, prompt: Prompt) -> Dict[str, Any]:
        """
        Execute a pipeline for the given prompt.
        
        This method sets up the execution environment, creates the Team
        and User objects, and runs the workflow with appropriate timeouts
        and resource management.
        
        Args:
            prompt: The parsed prompt to execute
            
        Returns:
            Dictionary containing execution results and metrics
            
        Raises:
            SessionError: If execution fails
        """
        self.start_time = datetime.now()
        
        try:
            # Set up team based on prompt reviewers
            team = self._setup_team(prompt.reviewers)
            
            # Create initial context with team and other required state
            context = Context(
                prompt=prompt,
                team=team
            )
            context.user = self.user
            
            async with asyncio.timeout(self.timeout):
                final_context = await self.pipeline.execute(context)
            
            self.end_time = datetime.now()
            
            # Write outputs atomically
            await self._write_outputs(final_context.outputs)
            
            # Create and return final result
            return self._create_result(final_context)


        except Exception as e:
            error_message = str(e)
            if isinstance(e, asyncio.TimeoutError):
                error_message = "TimeoutError"
            
            self.end_time = datetime.now()
            
            # Create error result with available metrics
            error_result = {
                "status": "error",
                "error": error_message,
                "execution_time": (self.end_time - self.start_time).total_seconds(),
                "usage": self.provider.usage
            }
            
            # Re-raise with original message and context
            raise SessionError(error_message, error_result)

    def _setup_team(self, reviewers: Set[str]) -> Team:
        """
        Create model instances for requested reviewers.
        
        Args:
            reviewers: Set of team members to include in the session
            
        Returns:
            Team instance with requested reviewers
            
        Raises:
            SessionError: If any requested team member isn't configured
        """
        llms = {}
        missing = []
        
        for name in reviewers:
            if name not in self.available_llms:
                missing.append(name)
                continue
            llms[name] = self.available_llms[name]
                        
        if missing:
            raise SessionError(
                f"Unknown team members: {', '.join(missing)} requested: {list(reviewers)}, available: {list(self.available_llms.keys())}",
                {}
            )
            
        return Team(llms)
    
    async def _write_outputs(self, outputs: Dict[str, str]) -> None:
        """
        Write output files atomically to their final locations.
        
        Args:
            outputs: Dictionary mapping paths to file content
            
        Raises:
            SessionError: If file operations fail
        """
        temp_files = {}
        
        try:
            # Create temporary directory if needed
            if not self._temp_dir:
                self._temp_dir = Path(tempfile.mkdtemp())
            
            # First write all files to temporary locations
            for path, content in outputs.items():
                assert(isinstance(path, Path))
                # Create full path including parent directories
                temp_path = self._temp_dir / path
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_text(content)
                temp_files[path] = temp_path
            
            # Then atomically move all files to their final locations
            for final_path, temp_path in temp_files.items():
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(temp_path), str(final_path))
                
        except Exception as e:
            # Clean up any temporary files
            for temp_path in temp_files.values():
                if temp_path.exists():
                    temp_path.unlink()
            
            raise SessionError(
                f"Failed to write outputs: {e}",
                {"attempted_files": list(outputs.keys())}
            )

    
    def _create_result(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the final execution result with metrics.
        
        Args:
            context: The final pipeline context
            
        Returns:
            Dictionary containing execution results and metrics
        """
        return {
            "status": "success",
            "outputs": context.outputs,
            "execution_time": (self.end_time - self.start_time).total_seconds(),
            "metrics": {
                "clarification_count": len(context.clarifications),
                "draft_count": len(context.drafts),
                "review_count": len(context.reviews),
                "file_count": len(context.outputs)
            },
            "usage": self.provider.usage
        }
