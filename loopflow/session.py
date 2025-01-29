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
from .workflow import default_pipeline, Job, WorkflowState
from .llm import LLMProvider, LLM
from .team import Team
import logging

# Configure logging with a specific format for loopflow
logger = logging.getLogger("loopflow")

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
        self.logger = logging.getLogger("loopflow.user")

    async def chat(self, prompt: str) -> str:
        """
        Chat with the user and return their response.
        """
        self.logger.info("Requesting user input")
        self.logger.debug("User prompt: %s", prompt)
        print("\n" + prompt + "\n")
        response = input("Your response: ")
        self.logger.debug("User response: %s", response)
        return response

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
        self.logger = logging.getLogger("loopflow.session")

        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._temp_dir: Optional[Path] = None
        
        assert(len(self.available_llms) > 0)
        self.logger.info("Session initialized with %d LLMs", len(self.available_llms))
        self.logger.debug("Available LLMs: %s", list(self.available_llms.keys()))

    
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
        self.logger.info("Starting session execution")
        self.logger.info("Goal: %s", prompt.goal)
        self.logger.debug("Output files: %s", prompt.output_files)
        if prompt.context_files:
            self.logger.debug("Context files: %s", prompt.context_files)
  
        try:
            # Set up team based on prompt team
            team = self._setup_team(prompt.team)
            self.logger.info("Team setup complete with %d members", len(team.llms))
            
            # Create initial context with team and other required state
            state = WorkflowState(
                prompt=prompt,
                team=team
            )
            state.user = self.user
            
            async with asyncio.timeout(self.timeout):
                final_context = await self.pipeline.execute(state)
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.info("Pipeline execution completed in %.2f seconds", duration)
            
            # Write outputs atomically
            await self._write_outputs(final_context.outputs)
            self.logger.info("Output files written successfully")
            
            # Create and return final result
            result = self._create_result(final_context)
            self.logger.info("Session completed successfully")
            self.logger.info("Total cost: $%.4f", self.provider.usage.totalCostUsd())
            return result

        except Exception as e:
            error_message = str(e)
            if isinstance(e, asyncio.TimeoutError):
                error_message = "TimeoutError"
            
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            self.logger.error("Session failed after %.2f seconds: %s", duration, error_message)
            
            # Create error result with available metrics
            error_result = {
                "status": "error",
                "error": error_message,
                "execution_time": duration,
                "usage": self.provider.usage
            }
            
            # Re-raise with original message and context
            raise SessionError(error_message, error_result)

    def _setup_team(self, team: Set[str]) -> Team:
        """
        Create model instances for requested team.
        
        Args:
            team: Set of team members to include in the session
            
        Returns:
            Team instance with requested team
            
        Raises:
            SessionError: If any requested team member isn't configured
        """
        self.logger.debug("Setting up team with members: %s", team)
        llms = {}
        missing = []
        
        for name in team:
            if name not in self.available_llms:
                missing.append(name)
                continue
            llms[name] = self.available_llms[name]
                        
        if missing:
            self.logger.error("Unknown team members requested: %s", missing)
            self.logger.error("Available team members: %s", list(self.available_llms.keys()))
            raise SessionError(
                f"Unknown team members: {', '.join(missing)} requested: {list(team)}, available: {list(self.available_llms.keys())}",
                {}
            )
            
        return Team(self.provider, llms)
    
    async def _write_outputs(self, outputs: Dict[str, str]) -> None:
        """
        Write output files atomically to their final locations.
        
        Args:
            outputs: Dictionary mapping paths to file content
            
        Raises:
            SessionError: If file operations fail
        """
        self.logger.info("Writing %d output files", len(outputs))
        temp_files = {}
        
        try:
            # Create temporary directory if needed
            if not self._temp_dir:
                self._temp_dir = Path(tempfile.mkdtemp())
                self.logger.debug("Created temp directory: %s", self._temp_dir)
            
            # First write all files to temporary locations
            for path, content in outputs.items():
                assert(isinstance(path, Path))
                # Create full path including parent directories
                temp_path = self._temp_dir / path
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_text(content)
                temp_files[path] = temp_path
                self.logger.debug("Wrote temporary file: %s", temp_path)
            
            # Then atomically move all files to their final locations
            for final_path, temp_path in temp_files.items():
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(temp_path), str(final_path))
                self.logger.debug("Moved file to final location: %s", final_path)
                
        except Exception as e:
            # Clean up any temporary files
            self.logger.error("Failed to write outputs: %s", e)
            for temp_path in temp_files.values():
                if temp_path.exists():
                    temp_path.unlink()
                    self.logger.debug("Cleaned up temporary file: %s", temp_path)
            
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
        result = {
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
        
        self.logger.debug("Session results: %s", result)
        return result
