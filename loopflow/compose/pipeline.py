"""
Pipeline implementation for loopflow.

This module defines pipelines that orchestrate jobs to execute specific workflows
for the composer CLI. Each pipeline combines one or more jobs to accomplish
a particular goal like clarifying requirements or generating code.
"""

import logging
import shutil
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from loopflow.compose.prompt import Prompt
from loopflow.io.session import Session
from loopflow.compose.job import Clarify, Draft, Review, Synthesize, JobError

logger = logging.getLogger(__name__)

class PipelineError(Exception):
    """Base error for pipeline failures."""
    def __init__(self, message: str, context: Dict[str, Any]):
        self.message = message
        self.context = context
        super().__init__(message)

class Pipeline(ABC):
    """
    Base class for all pipelines.
    
    A Pipeline represents a workflow that can be executed by the composer CLI.
    Each pipeline orchestrates one or more jobs to complete a specific workflow.
    """
    
    def __init__(self, session: Session, prompt: Prompt):
        """
        Initialize pipeline with session and prompt.
        
        Args:
            session: The shared session object
            prompt: The parsed prompt to execute
        """
        self.session = session
        self.prompt = prompt
        self.user = session.user
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self._temp_dir: Optional[Path] = None
        self.logger = logging.getLogger(f"loopflow.pipeline.{self.__class__.__name__.lower()}")
    
    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """
        Execute this pipeline and return results.
        
        Returns:
            Dictionary containing execution results
            
        Raises:
            PipelineError: If execution fails
        """
        pass
    
    async def _write_outputs(self, outputs: Dict[Path, str]) -> None:
        """
        Write output files atomically to their final locations.
        
        Args:
            outputs: Dictionary mapping paths to file content
            
        Raises:
            PipelineError: If file operations fail
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
                # Ensure the path is a Path object
                path = Path(path) if not isinstance(path, Path) else path
                
                # Create full path including parent directories
                temp_path = self._temp_dir / path.name
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
            
            raise PipelineError(
                f"Failed to write outputs: {e}",
                {"attempted_files": [str(p) for p in outputs.keys()]}
            )
    
    def _format_result(self, status: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the final result dictionary.
        
        Args:
            status: Status of the execution ('success' or 'error')
            data: Additional data to include in the result
            
        Returns:
            Result dictionary with standard fields
        """
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        result = {
            "status": status,
            "execution_time": duration,
            "total_cost": self.session.total_cost(),
            **data
        }
        
        return result

class ClarifyPipeline(Pipeline):
    """
    Pipeline for the 'clarify' command.
    
    Handles generating questions from teammates and appending them to the prompt file.
    """
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the clarify pipeline.
        
        Returns:
            Dictionary with clarification results
            
        Raises:
            PipelineError: If clarification fails
        """
        try:
            # Create and run the clarify job
            job = Clarify(self.session, self.prompt)
            result = await job.execute()
            
            # Extract questions from result
            questions = result.get('questions', {})
            
            # Append clarifications to the prompt file
            prompt_updated = await self._append_to_prompt_file(questions)
            
            return self._format_result("success", {
                "questions": questions,
                "prompt_updated": prompt_updated
            })
            
        except JobError as e:
            self.logger.error(f"Clarify job failed: {e}")
            return self._format_result("error", {
                "error": str(e),
                "context": e.context
            })
        except Exception as e:
            self.logger.error(f"Clarify pipeline failed: {e}")
            return self._format_result("error", {
                "error": str(e)
            })
    
    async def _append_to_prompt_file(
        self, 
        questions: Dict[str, str]
    ) -> bool:
        """
        Append clarifications to the prompt file.
        
        Args:
            questions: Dictionary mapping team members to their questions
            
        Returns:
            True if the prompt file was updated successfully
        """
        
        try:
            self.logger.info(f"Appending clarifications to {self.prompt.path}")
            with open(self.prompt.path, 'a') as f:
                f.write("\n\n## Questions\n")
                
                # Write each team member's questions as a separate section
                for mate_name, mate_questions in questions.items():
                    f.write(f"\n### {mate_name}'s questions\n{mate_questions}\n")
            
            self.logger.info("Successfully appended clarifications to prompt file")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to append clarifications to prompt file: {e}")
            return False

class MatePipeline(Pipeline):
    """
    Pipeline for the 'mate' command.
    
    Handles generating drafts from a single mate and writing outputs.
    """
    
    def __init__(self, session: Session, prompt: Prompt, mate_name: Optional[str] = None):
        """
        Initialize mate pipeline with session, prompt, and mate name.
        
        Args:
            session: The shared session object
            prompt: The parsed prompt to execute
            mate_name: Name of the mate to use (optional)
        """
        super().__init__(session, prompt)
        self.mate_name = mate_name
        
        # If no mate specified, use the first one from the prompt
        if not self.mate_name and self.prompt.team:
            self.mate_name = self.prompt.team[0]
            self.logger.info(f"No mate specified, using first mate: {self.mate_name}")
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the mate pipeline.
        
        Returns:
            Dictionary with draft results
            
        Raises:
            PipelineError: If drafting fails
        """
        if not self.mate_name:
            raise PipelineError("No mate specified and none found in prompt", {})
        
        try:
            # Create and run the draft job with a single mate
            job = Draft(self.session, self.prompt)
            result = await job.execute(mate_name=self.mate_name)
            
            # Extract drafts from result
            drafts = result.get('drafts', {}).get(self.mate_name, {})
            
            # Write the outputs
            await self._write_outputs(drafts)
            
            return self._format_result("success", {
                "mate": self.mate_name,
                "drafts": {str(path): len(content) for path, content in drafts.items()},
                "outputs": drafts
            })
            
        except JobError as e:
            self.logger.error(f"Mate pipeline job failed: {e}")
            return self._format_result("error", {
                "error": str(e),
                "mate": self.mate_name,
                "context": e.context
            })
        except Exception as e:
            self.logger.error(f"Mate pipeline failed: {e}")
            return self._format_result("error", {
                "error": str(e),
                "mate": self.mate_name
            })

class ReviewPipeline(Pipeline):
    """
    Pipeline for the 'review' command.
    
    Takes existing files and submits them for review by the team,
    then appends the reviews to the prompt file.
    """
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the review pipeline.
        
        Returns:
            Dictionary with review results
            
        Raises:
            PipelineError: If review fails
        """
        try:
            # Set up team
            team = self.session.setup_team(self.prompt.team)
            self.logger.info(f"Team set up with {len(team.llms)} members")
            
            # Read existing files to review
            drafts = await self._read_existing_files()
            if not drafts.get('user', {}):
                raise PipelineError("No existing files found to review", {
                    "expected_files": [str(p) for p in self.prompt.output_files]
                })
            
            # Run the review job
            review_job = Review(self.session, self.prompt)
            review_result = await review_job.execute(team=team, drafts=drafts)
            reviews = review_result.get('reviews', {})
            
            # Append reviews to the prompt file
            prompt_updated = await self._append_to_prompt_file(reviews)
            
            return self._format_result("success", {
                "team": list(team.llms.keys()),
                "files_reviewed": list(drafts['user'].keys()),
                "reviews": reviews,
                "prompt_updated": prompt_updated
            })
            
        except JobError as e:
            self.logger.error(f"Review job failed: {e}")
            return self._format_result("error", {
                "error": str(e),
                "context": e.context
            })
        except Exception as e:
            self.logger.error(f"Review pipeline failed: {e}")
            return self._format_result("error", {
                "error": str(e)
            })
    
    async def _read_existing_files(self) -> Dict[str, Dict[Path, str]]:
        """
        Read existing files specified in the prompt.
        
        Returns:
            Dictionary with 'user' as author and files as drafts
        """
        drafts = {'user': {}}
        
        for file_path in self.prompt.output_files:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"File not found: {path}")
                continue
                
            try:
                content = path.read_text()
                self.logger.info(f"Read file: {path} ({len(content)} chars)")
                drafts['user'][path] = content
            except Exception as e:
                self.logger.error(f"Error reading file {path}: {e}")
        
        return drafts
    
    async def _append_to_prompt_file(self, reviews: Dict[str, Dict[str, str]]) -> bool:
        """
        Append reviews to the prompt file.
        
        Args:
            reviews: Dictionary mapping reviewers to their reviews
            
        Returns:
            True if prompt file was updated successfully
        """
        
        try:
            self.logger.info(f"Appending reviews to {self.prompt.path}")
            with open(self.prompt.path, 'a') as f:
                f.write("\n\n## Reviews\n")
                
                # Write each reviewer's reviews
                for reviewer, author_reviews in reviews.items():
                    f.write(f"\n### {reviewer}'s review\n")
                    for author, review in author_reviews.items():
                        f.write(f"{review}\n")
            
            self.logger.info("Successfully appended reviews to prompt file")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to append reviews to prompt file: {e}")
            return False

class TeamPipeline(Pipeline):
    """
    Pipeline for the 'team' command.
    
    Handles the full draft-review-synthesize workflow with the entire team.
    """
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the team pipeline.
        
        Returns:
            Dictionary with team workflow results
            
        Raises:
            PipelineError: If the workflow fails
        """
        try:
            # Set up team once and reuse it across jobs
            team = self.session.setup_team(self.prompt.team)
            self.logger.info(f"Team set up with {len(team.llms)} members")
            
            # 1. DRAFT PHASE
            draft_job = Draft(self.session, self.prompt)
            draft_result = await draft_job.execute(team=team)
            drafts = draft_result.get('drafts', {})
            
            # 2. REVIEW PHASE
            review_job = Review(self.session, self.prompt)
            review_result = await review_job.execute(team=team, drafts=drafts)
            reviews = review_result.get('reviews', {})
            
            # 3. SYNTHESIS PHASE
            synthesize_job = Synthesize(self.session, self.prompt)
            synthesis_result = await synthesize_job.execute(
                team=team, 
                drafts=drafts,
                reviews=reviews
            )
            outputs = synthesis_result.get('outputs', {})
            
            # Write the final outputs
            await self._write_outputs(outputs)
            
            return self._format_result("success", {
                "team": list(team.llms.keys()),
                "draft_count": len(drafts),
                "review_count": len(reviews),
                "file_count": len(outputs),
                "outputs": outputs
            })
            
        except JobError as e:
            self.logger.error(f"Team pipeline job failed: {e}")
            return self._format_result("error", {
                "error": str(e),
                "team": self.prompt.team,
                "context": e.context
            })
        except Exception as e:
            self.logger.error(f"Team pipeline failed: {e}")
            return self._format_result("error", {
                "error": str(e),
                "team": self.prompt.team
            })  