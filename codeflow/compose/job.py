"""
Job implementations for codeflow.

This module defines the basic jobs that can be executed as part of a pipeline.
Each job represents a specific task like clarifying requirements, drafting files,
reviewing content, or synthesizing final outputs.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from codeflow.compose.prompt import Prompt
from codeflow.io.file import get_context
from codeflow.llm.mate import Team
from codeflow.io.session import Session
from codeflow.templates import (
    QUESTION_TEMPLATE,
    DRAFT_TEMPLATE,
    REVIEW_TEMPLATE,
    SYNTHESIS_TEMPLATE
)

logger = logging.getLogger(__name__)

class JobError(Exception):
    """Base error for job execution failures."""
    def __init__(self, message: str, context: Dict[str, Any]):
        self.message = message
        self.context = context
        super().__init__(message)

class Job(ABC):
    """
    Base class for all jobs.
    
    A job represents a specific task that can be executed as part of a pipeline.
    Jobs are self-contained units that take inputs and produce outputs.
    """
    
    def __init__(self, session: Session, prompt: Prompt):
        """
        Initialize job with session and prompt.
        
        Args:
            session: The shared session object
            prompt: The parsed prompt to execute
        """
        self.session = session
        self.prompt = prompt
        self.logger = logging.getLogger(f"codeflow.job.{self.__class__.__name__.lower()}")
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute this job and return results.
        
        Args:
            **kwargs: Additional job-specific parameters
            
        Returns:
            Dictionary containing job results
            
        Raises:
            JobError: If job execution fails
        """
        pass

class Clarify(Job):
    """Job that gathers clarification questions from teammates."""
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the clarification job.
        
        Args:
            team: Optional Team object to use (will be created if not provided)
            
        Returns:
            Dictionary with questions from each team member
            
        Raises:
            JobError: If clarification fails
        """
        team = kwargs.get('team') or self.session.setup_team(self.prompt.team)
        self.logger.info("Team set up with %d members", len(team.llms))
        
        try:
            # Gather questions from all models
            questions = await team.query_parallel(
                QUESTION_TEMPLATE.format(
                    goal=self.prompt.goal,
                    file_paths=("\n".join(str(p) for p in self.prompt.output_files)),
                    context=get_context(self.prompt.context_files),
                )
            )
            
            self.logger.info("Received questions from team members:")
            for name, q in questions.items():
                self.logger.info("  %s's questions (%d chars)", name, len(q))
                
            return {
                "questions": questions,
                "team": team
            }
            
        except Exception as e:
            self.logger.error("Clarification failed: %s", str(e), exc_info=True)
            raise JobError("Clarification failed", {
                "error": str(e),
                "stage": "clarify"
            })

class Draft(Job):
    """Job that generates drafts for specified files."""
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the draft job.
        
        Args:
            team: Optional Team object to use (will be created if not provided)
            mate_name: Optional name of a specific mate to use
            
        Returns:
            Dictionary with drafts and team information
            
        Raises:
            JobError: If drafting fails
        """
        # Get team or mate name from kwargs
        team = kwargs.get('team')
        mate_name = kwargs.get('mate_name')
        
        # Ensure we have either a team or a mate name
        if not team and not mate_name:
            # Default to using the whole team
            team = self.session.setup_team(self.prompt.team)
            self.logger.info("Using team with %d members", len(team.llms))
        elif mate_name and not team:
            # Create a single-mate team
            self.logger.info(f"Using single mate: {mate_name}")
            llm = self.session.get_llm(mate_name)
            team = Team(
                providers=self.session.providers,
                llms={mate_name: llm}
            )
        
        try:
            drafts = {name: {} for name in team.llms}
            
            # Generate drafts for each output file
            for file_path in self.prompt.output_files:
                self.logger.info(f"Generating drafts for {file_path}")
                
                draft_prompt = DRAFT_TEMPLATE.format(
                    file_path=str(file_path),
                    goal=self.prompt.goal,
                    context=get_context(self.prompt.context_files),
                )
                
                responses = await team.query_parallel(draft_prompt)
                self.logger.info(f"Received {len(responses)} drafts for {file_path}")
                
                for author, content in responses.items():
                    drafts[author][file_path] = content
                    self.logger.debug(f"Stored draft from {author} for {file_path} ({len(content)} chars)")
            
            return {
                "drafts": drafts,
                "team": team,
                "team_members": list(team.llms.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Draft job failed: {e}")
            raise JobError("Draft job failed", {
                "error": str(e),
                "mate": mate_name,
                "team": list(team.llms.keys()) if team else None
            })

class Review(Job):
    """Job that reviews drafts."""
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the review job.
        
        Args:
            team: Team object to use for reviews
            drafts: Drafts to review - dict mapping authors to their drafts
            
        Returns:
            Dictionary with reviews and team information
            
        Raises:
            JobError: If review fails
        """
        team = kwargs.get('team')
        drafts = kwargs.get('drafts')
        
        if not team:
            team = self.session.setup_team(self.prompt.team)
            self.logger.info("Using team with %d members", len(team.llms))
            
        if not drafts:
            raise JobError("No drafts provided for review", {
                "stage": "review"
            })
        
        try:
            reviews = {name: {} for name in team.llms}
            
            for author, author_drafts in drafts.items():
                self.logger.info(f"Processing reviews for {author}'s drafts")
                
                # Format drafts
                all_drafts_str = f"Draft by {author}:\n" + "\n\n".join(
                    f"## {file_path}:\n{content}" 
                    for file_path, content in author_drafts.items()
                )
                
                file_paths_str = "\n".join(str(p) for p in self.prompt.output_files)
                
                # Get reviews
                responses = await team.query_parallel(
                    REVIEW_TEMPLATE.format(
                        file_paths=file_paths_str,
                        goal=self.prompt.goal,
                        draft=all_drafts_str,
                        context=get_context(self.prompt.context_files),
                    )
                )
                
                self.logger.info(f"Received {len(responses)} reviews for {author}'s drafts")
                
                for reviewer, review in responses.items():
                    reviews[reviewer][author] = review
                    self.logger.debug(f"Stored review from {reviewer} for {author} ({len(review)} chars)")
            
            return {
                "reviews": reviews,
                "team": team
            }
            
        except Exception as e:
            self.logger.error(f"Review job failed: {e}")
            raise JobError("Review job failed", {
                "error": str(e),
                "stage": "review"
            })

class Synthesize(Job):
    """Job that synthesizes final content from drafts and reviews."""
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the synthesis job.
        
        Args:
            team: Team object to use for synthesis
            drafts: Drafts to synthesize - dict mapping authors to their drafts
            reviews: Reviews of drafts - dict mapping reviewers to their reviews
            synthesizer_name: Optional name of mate to use as synthesizer
            
        Returns:
            Dictionary with outputs and synthesizer information
            
        Raises:
            JobError: If synthesis fails
        """
        team = kwargs.get('team')
        drafts = kwargs.get('drafts')
        reviews = kwargs.get('reviews')
        synthesizer_name = kwargs.get('synthesizer_name')
        
        if not team:
            team = self.session.setup_team(self.prompt.team)
            self.logger.info("Using team with %d members", len(team.llms))
            
        if not drafts:
            raise JobError("No drafts provided for synthesis", {
                "stage": "synthesize"
            })
            
        if not reviews:
            raise JobError("No reviews provided for synthesis", {
                "stage": "synthesize"
            })
        
        try:
            outputs = {}
            
            # Pick synthesizer (prefer provided name, then first mate)
            if synthesizer_name and synthesizer_name in team.llms:
                pass  # Use provided name
            else:
                synthesizer_name = next(iter(team.llms.keys()))
                
            synthesizer = team.llms[synthesizer_name]
            self.logger.info(f"Selected synthesizer: {synthesizer_name}")
            
            for file_path in self.prompt.output_files:
                self.logger.info(f"Synthesizing file: {file_path}")
                
                # Normalize path
                if isinstance(file_path, str):
                    file_path = Path(file_path)
                
                # Collect drafts and reviews
                drafts_and_reviews = []
                for author, author_drafts in drafts.items():
                    draft = self._get_draft_by_path(author_drafts, file_path)
                    
                    if not draft:
                        self.logger.warning(f"No draft found for {file_path} from {author}")
                        continue
                    
                    draft_str = f"Draft by {author}:\n{draft}\n"
                    
                    reviews_str = "\n\n".join(
                        f"Review by {reviewer}:\n{review_dict.get(author, 'No review')}\n" 
                        for reviewer, review_dict in reviews.items()
                    )
                    
                    combined = f"{draft_str}\n\nReviews:\n{reviews_str}\n"
                    drafts_and_reviews.append(combined)
                
                if not drafts_and_reviews:
                    self.logger.error(f"No drafts found for {file_path}")
                    continue
                
                # Generate synthesis
                full_context = "\n\n".join(drafts_and_reviews)
                
                synthesis_prompt = SYNTHESIS_TEMPLATE.format(
                    file_path=str(file_path),
                    drafts_and_reviews=full_context,
                    goal=self.prompt.goal,
                    context=get_context(self.prompt.context_files),
                )
                
                final_content = await synthesizer.chat(synthesis_prompt)
                self.logger.info(f"Received synthesized content for {file_path} ({len(final_content)} chars)")
                
                outputs[file_path] = final_content
            
            return {
                "outputs": outputs,
                "synthesizer": synthesizer_name
            }
            
        except Exception as e:
            self.logger.error(f"Synthesis job failed: {e}")
            raise JobError("Synthesis job failed", {
                "error": str(e),
                "stage": "synthesize"
            })
    
    def _get_draft_by_path(self, drafts: Dict[Path, str], target_path: Path) -> Optional[str]:
        """
        Find a draft that matches the target path, handling path inconsistencies.
        
        Args:
            drafts: Dictionary of drafts by path
            target_path: The path to find
            
        Returns:
            The draft content if found, None otherwise
        """
        # Try direct match
        if target_path in drafts:
            return drafts[target_path]
        
        # Try string representation
        target_str = str(target_path)
        for path, content in drafts.items():
            path_str = str(path)
            if path_str == target_str:
                return content
            
            # Try resolving and comparing
            try:
                if Path(path).resolve() == target_path.resolve():
                    return content
            except:
                pass  # Ignore resolution errors
        
        # Not found
        return None