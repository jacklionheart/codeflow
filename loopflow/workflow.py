"""
Workflow implementation for loopflow.

This module defines the core workflow jobs and their composition. Each job
represents a distinct phase in the generation process (clarification, drafting,
review, and synthesis), and can be composed into pipelines for execution.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

from .prompt import Prompt
from .llm import LLM
from .team import Team    
from .templates import (
    QUESTION_TEMPLATE,
    DRAFT_TEMPLATE,
    REVIEW_TEMPLATE,
    SYNTHESIS_TEMPLATE
)

class WorkflowError(Exception):
    """Base error for workflow failures with context."""
    def __init__(self, message: str, context: Dict[str, Any]):
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
# Context
# -----------------------------------------------------------------------------

@dataclass
class Context:
    """
    The shared context passed between pipeline jobs.
    
    The Context maintains all state accumulated during workflow execution,
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
    takes a Context as input, performs some work (possibly involving LLM
    interactions or user input), and returns an updated Context.
    """

    @abstractmethod
    async def execute(self, context: Context) -> Context:
        """
        Execute this job's work and return updated context.
        
        Args:
            context: The current workflow context
            
        Returns:
            Updated context with this job's results
            
        Raises:
            WorkflowError: If job execution fails
        """
        pass

# -----------------------------------------------------------------------------
# Job Implementations 
# -----------------------------------------------------------------------------

class Clarify(Job):
    """
    Job that handles requirement clarification through model interaction.
    
    The Clarify job has models ask questions about the requirements and
    collects answers from the user. This helps ensure alignment before
    generation begins.
    """
    
    async def execute(self, context: Context) -> Context:
        try:
            # Gather questions from all models, customizing priorities per teammate
            questions = await context.team.query_parallel(
                QUESTION_TEMPLATE,
                {
                    "goal": context.prompt.goal,
                    "file_paths": "\n".join(str(p) for p in context.prompt.output_files),
                    "context": "\n".join(str(p) for p in (context.prompt.context_files or [])),
                    "priorities": lambda name: context.team.get_teammate_priorities(name)
                }
            )

            # Format questions for user
            questions_str = "\n\n".join(
                f"{name}'s Questions:\n{q}" 
                for name, q in questions.items()
            )
            context.log_step("questions", {"questions": questions})

            # Get user answers
            user_answers = await context.user.chat(questions_str)
            context.log_step("answers", {"answers": user_answers})
            
            # Store Q&A pairs
            context.clarifications = {
                "questions": questions_str,
                "answers": user_answers
            }
            
            return context
            
        except Exception as e:
            raise WorkflowError("Clarification failed", {
                "error": str(e),
                "stage": "clarify"
            })

class Draft(Job):
    """
    Job that generates initial code drafts for each file using all models.
    
    The Draft job has each model generate initial implementations for all
    required files. These drafts serve as the starting point for review
    and iteration.
    """
    
    async def execute(self, context: Context) -> Context:
        try:
            prompt_data = context.prompt
            
            # Format clarification dialogue
            clar_text = (
                f"Questions:\n{context.clarifications['questions']}\n\n"
                f"Answers:\n{context.clarifications['answers']}"
                if context.clarifications
                else ""
            )
            
            # Initialize draft storage for each author
            for name in context.team.llms:
                context.drafts[name] = {}

            # Generate drafts for each output file
            for file_path in prompt_data.output_files:
                # Query all models in parallel for a draft
                responses = await context.team.query_parallel(
                    DRAFT_TEMPLATE,
                    {
                        "goal": prompt_data.goal,
                        "file_path": str(file_path),
                        "clarification_dialogue": clar_text,
                        "priorities": lambda name: context.team.get_teammate_priorities(name)
                    }
                )
                
                # Store each author's draft
                for model_name, draft_text in responses.items():
                    context.drafts[model_name][Path(file_path)] = draft_text
                    
                context.log_step("draft", {
                    "file": str(file_path),
                    "drafts": responses
                })
            
            return context
            
        except Exception as e:
            raise WorkflowError("Draft generation failed", {
                "error": str(e),
                "stage": "draft"
            })

class Review(Job):
    """
    Job that handles code review feedback from each model.
    
    The Review job has each model review all drafts, providing structured
    feedback according to their priorities and expertise.
    """
    
    async def execute(self, context: Context) -> Context:
        try:
            # Initialize review storage
            for reviewer in context.team.llms:
                context.reviews[reviewer] = {}

            # Have each team member review each author's drafts
            for author, draft_dict in context.drafts.items():
                # Format all drafts from this author
                all_drafts_str = f"Draft by {author}:\n" + "\n\n".join(
                    f"## {file_path}:\n{content}" 
                    for file_path, content in draft_dict.items()
                )

                responses = await context.team.query_parallel(
                    REVIEW_TEMPLATE,
                    {
                        "file_paths": "\n".join(str(p) for p in context.prompt.output_files),
                        "draft": all_drafts_str,
                        "priorities": lambda name: context.team.get_teammate_priorities(name)
                    }
                )
                
                for reviewer_name, review_text in responses.items():
                    context.reviews[reviewer_name][author] = review_text
                    
                context.log_step("review", {
                    "author": author,
                    "reviews": responses
                })
            
            return context
            
        except Exception as e:
            raise WorkflowError("Review failed", {
                "error": str(e),
                "stage": "review"
            })

class Synthesize(Job):
    """
    Job that creates final versions of each file by combining
    the best elements of all drafts while addressing review feedback.
    
    The Synthesize job analyzes all drafts and reviews to create optimal
    final implementations that incorporate the best ideas and address
    key concerns.
    """
    
    async def execute(self, context: Context) -> Context:
        try:
            # Pick synthesizer (prefer 'maya' if available)
            synthesizer_name = "maya"
            if synthesizer_name not in context.team.llms:
                synthesizer_name = next(iter(context.team.llms.keys()))
            synthesizer = context.team.llms[synthesizer_name]

            # Process each output file
            for file_path in context.prompt.output_files:
                # Collect all drafts and reviews for this file
                author_drafts_and_reviews = []
                for author, draft_dict in context.drafts.items():
                    if file_path not in draft_dict:
                        continue
                        
                    draft_str = f"Draft by {author}:\n{draft_dict[file_path]}\n"
                    reviews_str = "\n\n".join(
                        f"Review by {reviewer}:\n{review_dict.get(author, 'No review')}\n" 
                        for reviewer, review_dict in context.reviews.items()
                    )
                    author_drafts_and_reviews.append(f"{draft_str}\n\nReviews:\n{reviews_str}\n")

                full_context = "\n\n".join(author_drafts_and_reviews)
            
                # Generate synthesized version
                combined_prompt = SYNTHESIS_TEMPLATE.format(
                    file_path=str(file_path),
                    drafts_and_reviews=full_context
                )

                final_content = await synthesizer.chat(combined_prompt)
                context.outputs[file_path] = final_content
                
                context.log_step("synthesize", {
                    "file": str(file_path),
                    "content": final_content
                })
            
            return context
            
        except Exception as e:
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
    
    Sequential provides a way to combine multiple jobs into a pipeline
    where each job's output context becomes the input context for the
    next job.
    """
    
    def __init__(self, jobs: List[Job]):
        """
        Initialize with list of jobs to execute in sequence.
        
        Args:
            jobs: List of Job instances to execute in order
        """
        self.jobs = jobs
    
    async def execute(self, context: Context) -> Context:
        """
        Execute all jobs in sequence, passing context through each.
        
        Args:
            context: Initial workflow context
            
        Returns:
            Final context after all jobs complete
            
        Raises:
            WorkflowError: If any job fails
        """
        current_context = context
        for job in self.jobs:
            current_context = await job.execute(current_context)
        return current_context

# -----------------------------------------------------------------------------
# Default Pipeline
# -----------------------------------------------------------------------------

def default_pipeline() -> Job:
    """
    Create the standard generation pipeline.
    
    Returns:
        A Sequential job combining the standard workflow:
        1. Clarify requirements
        2. Generate initial drafts
        3. Review all drafts
        4. Synthesize final versions
    """
    return Sequential([
        Clarify(),
        Draft(),
        Review(),
        Synthesize()
    ])