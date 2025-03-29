"""
Workflow implementation for loopflow.

This module defines the core workflow jobs and their composition. Each job
represents a distinct phase in the generation process (clarification, drafting,
review, and synthesis), and can be composed into pipelines for execution.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from .prompt import Prompt
from loopflow.llm.team import Team    
from loopflow.compose.file import get_context
from loopflow.templates import (
    QUESTION_TEMPLATE,
    DRAFT_TEMPLATE,
    REVIEW_TEMPLATE,
    SYNTHESIS_TEMPLATE
)

class WorkflowError(Exception):
    """Base error for workflow failures with state."""
    def __init__(self, message: str, context: Dict[str, Any]):
        self.message = message
        self.context = context
        super().__init__(message)

class RetryableError(WorkflowError):
    """Error that should trigger a retry of the job."""
    pass

async def with_retries(func, max_retries=3):
    """Execute a function with retries and exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)

# -----------------------------------------------------------------------------
# WorkflowState
# -----------------------------------------------------------------------------

@dataclass
class WorkflowState:
    """
    The shared state passed between pipeline jobs.
    
    The WorkflowState maintains all state accumulated during workflow execution,
    from the initial prompt through to final outputs. This includes all
    intermediate artifacts like clarifications, drafts, and reviews.
    """
    # Required initial state
    prompt: Prompt
    team: Team
    
    # State accumulated during execution
    clarifications: Dict[str, str] = field(default_factory=dict)  # Q -> A pairs
    # Author -> Path -> Content
    drafts: Dict[str, Dict[Path, str]] = field(default_factory=dict)
    # Reviewer -> Author -> Content
    reviews: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # Final outputs
    outputs: Dict[Path, str] = field(default_factory=dict)
    
    # Execution tracking
    start_time: datetime = field(default_factory=datetime.now)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def log_step(self, step: str, data: Dict[str, Any]) -> None:
        """Record execution step for debugging and metrics."""
        self.history.append({
            "step": step,
            "timestamp": datetime.now(),
            "data": data
        })

# -----------------------------------------------------------------------------
# Job Base Class
# -----------------------------------------------------------------------------

class Job(ABC):
    """
    Base class for all pipeline jobs.
    
    A Job represents a distinct phase in the generation process. Each job
    takes a WorkflowState as input, performs some work (possibly involving LLM
    interactions or user input), and returns an updated WorkflowState.
    """

    @abstractmethod
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """
        Execute this job's work and return updated state.
        
        Args:
            state: The current workflow state
            
        Returns:
            Updated state with this job's results
            
        Raises:
            WorkflowError: If job execution fails
        """
        pass

# -----------------------------------------------------------------------------
# Job Implementations 
# -----------------------------------------------------------------------------

class Clarify(Job):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        logger = logging.getLogger(__name__).getChild("clarify")
        logger.info("Starting clarification phase")
        start_time = datetime.now()
        
        try:
            # Log initial state
            logger.info("Initial state:")
            logger.info("  Goal: %s", state.prompt.goal)
            logger.info("  Team members: %s", list(state.team.llms.keys()))
            logger.info("  Output files: %s", [str(p) for p in state.prompt.output_files])
            
            # Gather questions from all models
            questions = await state.team.query_parallel(
                QUESTION_TEMPLATE,
                {
                    "goal": state.prompt.goal,
                    "file_paths": "\n".join(str(p) for p in state.prompt.output_files),
                    "context": get_context(state.prompt.context_files),
                }
            )
            
            logger.info("Received questions from team members:")
            for name, q in questions.items():
                logger.info("  %s's questions (%d chars):\n%s", name, len(q), q)
            
            # Format and get user response
            questions_str = "\n\n".join(
                f"{name}'s Questions:\n{q}" 
                for name, q in questions.items()
            )
            
            user_answers = await state.user.chat(questions_str)
            logger.info("Received user answers (%d chars):\n%s", len(user_answers), user_answers)
            
            # Store Q&A pairs
            state.clarifications = {
                "questions": questions_str,
                "answers": user_answers
            }
            logger.info("Stored clarifications in state")
            
            duration = (datetime.now() - start_time).total_seconds()
            cost = state.team.total_cost()
            logger.info("Clarification complete - Duration: %.2f seconds, Cost: $%.4f", 
                       duration, cost)
            
            return state
            
        except Exception as e:
            logger.error("Clarification failed: %s", str(e), exc_info=True)
            raise WorkflowError("Clarification failed", {
                "error": str(e),
                "stage": "clarify"
            })

class Draft(Job):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        logger = logging.getLogger(__name__).getChild("draft")
        logger.info("Starting draft generation phase")
        start_time = datetime.now()
        
        try:
            prompt_data = state.prompt
            logger.info("Processing prompt:")
            logger.info("  Goal: %s", prompt_data.goal)
            logger.info("  Output files: %s", [str(p) for p in prompt_data.output_files])
            
            # Format clarification dialogue
            clar_text = (
                f"Questions:\n{state.clarifications['questions']}\n\n"
                f"Answers:\n{state.clarifications['answers']}"
                if state.clarifications
                else ""
            )
            logger.debug("Using clarification text (%d chars)", len(clar_text))
            
            # Initialize draft storage
            for name in state.team.llms:
                state.drafts[name] = {}
                logger.info("Initialized draft storage for %s", name)

            # Generate drafts for each output file
            for file_path in prompt_data.output_files:
                logger.info("Generating drafts for: %s", file_path)
                                
                # Query models
                draft_prompt = DRAFT_TEMPLATE.format(
                    goal=prompt_data.goal,
                    file_path=str(file_path),
                    clarification_dialogue=clar_text,
                )
                
                logger.debug("Requesting drafts with prompt (%d chars)", len(draft_prompt))
                responses = await state.team.query_parallel(
                    draft_prompt,
                    {}
                )
                logger.info("Received %d drafts", len(responses))
                
                # Store drafts
                for model_name, draft_text in responses.items():
                    state.drafts[model_name][file_path] = draft_text
                    logger.info("Stored draft from %s for %s (%d chars)", 
                              model_name, file_path, len(draft_text))
                    logger.debug("Draft content preview:\n%s", draft_text[:500] + "...")
                
                state.log_step("draft", {
                    "file": str(file_path),
                    "drafts": {name: len(text) for name, text in responses.items()}
                })
            
            # Log final draft state
            logger.info("Final draft state:")
            for author, drafts in state.drafts.items():
                logger.info("  %s:", author)
                for path, content in drafts.items():
                    logger.info("    %s: %d chars", path, len(content))
            
            duration = (datetime.now() - start_time).total_seconds()
            cost = state.team.total_cost()
            logger.info("Draft generation complete - Duration: %.2f seconds, Cost: $%.4f",
                       duration, cost)
            
            return state
            
        except Exception as e:
            logger.error("Draft generation failed: %s", str(e), exc_info=True)
            raise WorkflowError("Draft generation failed", {
                "error": str(e),
                "stage": "draft"
            })

class Review(Job):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        logger = logging.getLogger(__name__).getChild("review")
        logger.info("Starting review phase")
        start_time = datetime.now()
        
        try:
            # Initialize review storage and log initial state
            logger.info("Initial state:")
            logger.info("  Drafts available from: %s", list(state.drafts.keys()))
            for name, drafts in state.drafts.items():
                logger.info("    %s has drafts for: %s", name, [str(p) for p in drafts.keys()])
            
            for reviewer in state.team.llms:
                state.reviews[reviewer] = {}
                logger.info("Initialized review storage for %s", reviewer)

            # Process each author's drafts
            for author, draft_dict in state.drafts.items():
                logger.info("Processing reviews for author: %s", author)
                
                # Format drafts
                all_drafts_str = f"Draft by {author}:\n" + "\n\n".join(
                    f"## {file_path}:\n{content}" 
                    for file_path, content in draft_dict.items()
                )
                logger.debug("Formatted drafts for review (%d chars)", len(all_drafts_str))
                
                # Get reviews - ensure we pass correct template parameters
                file_paths_str = "\n".join(str(p) for p in state.prompt.output_files)
                
                # Create template args dict explicitly
                template_args = {
                    "file_paths": file_paths_str,
                    "draft": all_drafts_str,
                }
                
                responses = await state.team.query_parallel(
                    REVIEW_TEMPLATE,
                    template_args
                )
                logger.info("Received %d reviews", len(responses))
                
                # Store reviews
                for reviewer_name, review_text in responses.items():
                    state.reviews[reviewer_name][author] = review_text
                    logger.info("Stored review from %s for %s's drafts (%d chars)", 
                              reviewer_name, author, len(review_text))
                    logger.debug("Review preview:\n%s", review_text[:500] + "...")
                    
                state.log_step("review", {
                    "author": author,
                    "reviews": {name: len(text) for name, text in responses.items()}
                })
            
            # Log final review state
            logger.info("Final review state:")
            for reviewer, reviews in state.reviews.items():
                logger.info("  %s reviewed:", reviewer)
                for author, review in reviews.items():
                    logger.info("    %s's drafts: %d chars", author, len(review))
            
            duration = (datetime.now() - start_time).total_seconds()
            cost = state.team.total_cost()
            logger.info("Review phase complete - Duration: %.2f seconds, Cost: $%.4f",
                       duration, cost)
            
            return state
            
        except Exception as e:
            logger.error("Review phase failed: %s", str(e), exc_info=True)
            raise WorkflowError("Review failed", {
                "error": str(e),
                "stage": "review",
                "author": author if 'author' in locals() else None,
                "reviewer": reviewer_name if 'reviewer_name' in locals() else None
            })

class Synthesize(Job):
    async def execute(self, state: WorkflowState) -> WorkflowState:
        logger = logging.getLogger(__name__).getChild("synthesize")
        logger.info("Starting synthesis phase")
        start_time = datetime.now()
        
        try:
            # Pick synthesizer
            synthesizer_name = "maya"
            if synthesizer_name not in state.team.llms:
                synthesizer_name = next(iter(state.team.llms.keys()))
            synthesizer = state.team.llms[synthesizer_name]
            logger.info("Selected synthesizer: %s", synthesizer_name)
            
            # Log initial state with extra path details
            logger.info("Initial state:")
            logger.info("  Drafts available from: %s", list(state.drafts.keys()))
            for author, drafts in state.drafts.items():
                logger.info("    %s has drafts for: %s (%s)", 
                    author, 
                    [str(p) for p in drafts.keys()],
                    [type(p).__name__ for p in drafts.keys()]
                )
            logger.info("  Reviews available from: %s", list(state.reviews.keys()))
            for reviewer, reviews in state.reviews.items():
                logger.info("    %s reviewed: %s", reviewer, list(reviews.keys()))

            # Process each output file
            for file_path in state.prompt.output_files:
                logger.info("Synthesizing file: %s (type: %s)", file_path, type(file_path).__name__)
                
                # Ensure consistent Path type
                if isinstance(file_path, str):
                    file_path = Path(file_path)
                
                # Normalize path for comparison
                file_path = file_path.resolve()
                
                # Debug logging for path comparison
                logger.debug("Looking for drafts with path: %s", file_path)
                for author, drafts in state.drafts.items():
                    logger.debug("  %s drafts:", author)
                    for draft_path in drafts.keys():
                        logger.debug("    %s (type: %s)", draft_path, type(draft_path).__name__)
                
                # Collect drafts and reviews
                author_drafts_and_reviews = []
                for author, draft_dict in state.drafts.items():
                    # Try both the path and its string representation
                    draft_text = None
                    if file_path in draft_dict:
                        draft_text = draft_dict[file_path]
                    elif str(file_path) in draft_dict:
                        draft_text = draft_dict[str(file_path)]
                    else:
                        # Try resolving paths
                        for draft_path in draft_dict.keys():
                            if isinstance(draft_path, str):
                                draft_path = Path(draft_path)
                            if draft_path.resolve() == file_path:
                                draft_text = draft_dict[draft_path]
                                break
                    
                    if draft_text is None:
                        logger.warning("No draft found for %s from %s", file_path, author)
                        continue
                        
                    draft_str = f"Draft by {author}:\n{draft_text}\n"
                    reviews_str = "\n\n".join(
                        f"Review by {reviewer}:\n{review_dict.get(author, 'No review')}\n" 
                        for reviewer, review_dict in state.reviews.items()
                    )
                    combined = f"{draft_str}\n\nReviews:\n{reviews_str}\n"
                    author_drafts_and_reviews.append(combined)
                    logger.info("Added draft+reviews for %s (%d chars)", author, len(combined))

                logger.info("Collected %d drafts with reviews", len(author_drafts_and_reviews))
                if not author_drafts_and_reviews:
                    error_msg = f"No drafts found for {file_path}"
                    logger.error(error_msg)
                    logger.error("Available drafts: %s", {
                        author: [str(p) for p in drafts.keys()]
                        for author, drafts in state.drafts.items()
                    })
                    raise WorkflowError(error_msg, {
                        "file": str(file_path),
                        "available_drafts": {
                            author: [str(p) for p in drafts.keys()]
                            for author, drafts in state.drafts.items()
                        }
                    })
                
                # Generate synthesis
                full_context = "\n\n".join(author_drafts_and_reviews)
                
                synthesis_prompt = SYNTHESIS_TEMPLATE.format(
                    file_path=str(file_path),
                    drafts_and_reviews=full_context
                )
                logger.debug("Synthesis prompt prepared (%d chars)", len(synthesis_prompt))

                logger.info("Requesting synthesis for: %s", file_path)
                final_content = await synthesizer.chat(synthesis_prompt)
                logger.info("Received synthesized content (%d chars)", len(final_content))
                logger.debug("Content preview:\n%s", final_content[:500] + "...")
                
                # Store result
                state.outputs[file_path] = final_content
                logger.info("Stored synthesized output for %s", file_path)
                
                state.log_step("synthesize", {
                    "file": str(file_path),
                    "content_length": len(final_content)
                })
            
            # Log final state
            logger.info("Final output state:")
            for path, content in state.outputs.items():
                logger.info("  %s: %d chars", path, len(content))
            
            duration = (datetime.now() - start_time).total_seconds()
            cost = state.team.total_cost()
            logger.info("Synthesis complete - Duration: %.2f seconds, Cost: $%.4f",
                       duration, cost)
            
            return state
            
        except Exception as e:
            logger.error("Synthesis failed: %s", str(e), exc_info=True)
            raise WorkflowError("Synthesis failed", {
                "error": str(e),
                "stage": "synthesize",
                "file": str(file_path) if 'file_path' in locals() else None
            })

# -----------------------------------------------------------------------------
# Sequential Job Composition
# -----------------------------------------------------------------------------

class Sequential(Job):
    """
    Composes multiple jobs into a single job, running them in order.
    """
    
    def __init__(self, jobs: List[Job]):
        """Initialize with list of jobs to execute in sequence."""
        super().__init__()
        self.jobs = jobs
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        logger = logging.getLogger(__name__).getChild("sequential")
        logger.info("Starting sequential pipeline with %d jobs", len(self.jobs))
        start_time = datetime.now()
        
        current_context = state
        for i, job in enumerate(self.jobs, 1):
            job_name = job.__class__.__name__
            logger.info("Starting job %d/%d: %s", i, len(self.jobs), job_name)
            
            try:
                current_context = await job.execute(current_context)
                usage = state.team.total_cost()
                logger.info(
                    "Completed job %s - Current cost: $%.4f", 
                    job_name, usage
                )
            except Exception as e:
                logger.error("Job %s failed: %s", job_name, str(e))
                raise
        
        duration = (datetime.now() - start_time).total_seconds()
        usage = state.team.total_cost()
        logger.info(
            "Pipeline complete - Total duration: %.2f seconds, Total cost: $%.4f",
            duration, usage
        )
        
        return current_context

# -----------------------------------------------------------------------------
# Default Pipeline
# -----------------------------------------------------------------------------

def default_pipeline() -> Job:
    """
    Create the standard generation pipeline.
    
    Returns:
        A Sequential job combining:
        1. Clarify requirements
        2. Generate initial drafts
        3. Review all drafts
        4. Synthesize final versions
    """
    logger = logging.getLogger(__name__)
    logger.debug("Creating default pipeline")
    pipeline = Sequential([
        Clarify(),
        Draft(),
        Review(),
        Synthesize()
    ])
    logger.debug("Default pipeline created with 4 jobs")
    return pipeline
