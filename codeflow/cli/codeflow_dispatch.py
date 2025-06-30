# codeflow/cli/codeflow.py
"""
Command-line interface for codeflow.

This module provides the main entry points for running codeflow from the
command line. It handles command parsing, configuration loading, and
execution setup while delegating the actual work to the pipelines.
"""

import asyncio
import logging
import os
import yaml
from pathlib import Path
import click
from typing import Optional, Dict, Any, Tuple

from codeflow.io.session import Session, Config, CLIUser
from codeflow.compose.prompt import Prompt
from codeflow.compose.pipeline import (
    ClarifyPipeline, 
    MatePipeline, 
    TeamPipeline, 
    ReviewPipeline,
)
from codeflow.io.git import auto_checkpoint, find_last_non_codeflow_commit, rebase_to_commit

logger = logging.getLogger("codeflow.cli")

class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass

class ProjectError(Exception):
    """Exception raised for project structure errors."""
    pass

def find_codeflow_file(project_dir: Path) -> Path:
    """
    Find the codeflow.md file in the project directory.
    
    Args:
        project_dir: Directory to search in
        
    Returns:
        Path to the codeflow.md file
        
    Raises:
        ProjectError: If codeflow.md file is not found
    """
    codeflow_file = project_dir / "codeflow.md"
    
    if not codeflow_file.exists():
        raise ProjectError(
            f"codeflow.md not found in {project_dir}. "
            f"Run 'codeflow init {project_dir}' to create a new project."
        )
    
    return codeflow_file

def setup_logging(debug: bool) -> None:
    """Configure logging with appropriate level and format."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger().setLevel(logging.INFO)
    logger = logging.getLogger("codeflow")
    logger.setLevel(log_level)

def create_session(config_path: Optional[Path], debug: bool) -> Tuple[Session, Dict[str, Any]]:
    """Create a session with the provided configuration."""
    config_obj = Config(
        config_path=config_path,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        debug=debug
    )
    
    user = CLIUser()
    session = Session(user, config_obj)
    
    # Load git configuration
    config_data = {}
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Error loading config file: {e}")
    
    return session, config_data

@click.group()
def cli():
    """Codeflow - Orchestrate LLM collaboration for file generation."""
    pass

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to config file (default: ~/.codeflow/config.yaml)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def clarify(project_dir: Path, config: Optional[Path], debug: bool, checkpoint: bool):
    """Generate questions to clarify requirements.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        setup_logging(debug)
        logger.info("Starting clarify with project directory: %s", project_dir)
        
        # Find and parse codeflow.md
        prompt_file = find_codeflow_file(project_dir)
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed successfully from %s", prompt_file)
        
        # Create session and pipeline
        session, config_data = create_session(config, debug)
        pipeline = ClarifyPipeline(session, prompt)
        
        # Auto-checkpoint if enabled
        if checkpoint:
            auto_checkpoint(project_dir, "clarify", prompt)

        # Execute pipeline
        result = asyncio.run(pipeline.execute())
                
        # Display results
        if result["status"] == "success":
            click.echo("Questions have been appended to the prompt file.")
            click.echo("Please add your answers and then run 'codeflow team' or 'codeflow mate'.")
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            if debug and 'context' in result:
                click.echo(f"Context: {result['context']}")
            
        logger.info("Clarify completed with status: %s", result["status"])
        
    except Exception as e:
        logger.error("Clarify failed: %s", str(e), exc_info=debug)
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()
    
@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to config file (default: ~/.codeflow/config.yaml)')
@click.option('--mate', '-m', help='Specific mate to use (default: use full team)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def draft(project_dir: Path, config: Optional[Path], mate: Optional[str], debug: bool, checkpoint: bool):
    """Generate drafts with either a specific mate or the full team.
    
    If using a specific mate, only the drafting phase is executed.
    If no mate is specified, runs the full team workflow with review and synthesis.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        setup_logging(debug)
        logger.info("Starting draft with project directory: %s", project_dir)
        
        # Find and parse codeflow.md
        prompt_file = find_codeflow_file(project_dir)
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed successfully from %s", prompt_file)
        
        # Auto-checkpoint if enabled
        if checkpoint:
            auto_checkpoint(project_dir, "draft", prompt)
        
        # Create session
        session, config_data = create_session(config, debug)
        
        # Choose pipeline based on whether a specific mate was requested
        if mate:
            logger.info(f"Using single mate pipeline with: {mate}")
            pipeline = MatePipeline(session, prompt, mate_name=mate)
        else:
            logger.info("Using full team pipeline")
            pipeline = TeamPipeline(session, prompt)
        
        # Execute pipeline
        result = asyncio.run(pipeline.execute())
                
        # Display results
        if result["status"] == "success":
            if mate:
                # Single mate output
                click.echo(f"Generated {len(result.get('outputs', {}))} files with mate: {result.get('mate', 'unknown')}")
                for path, content in result.get('outputs', {}).items():
                    click.echo(f"  - {path}: {len(content)} chars")
            else:
                # Team output
                click.echo(f"Generated {len(result.get('outputs', {}))} files using team: {', '.join(result.get('team', []))}")
                for path, _ in result.get('outputs', {}).items():
                    click.echo(f"  - {path}")
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            if debug and 'context' in result:
                click.echo(f"Context: {result['context']}")
        
        logger.info("Draft completed with status: %s", result["status"])
        
    except Exception as e:
        logger.error("Draft failed: %s", str(e), exc_info=debug)
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to config file (default: ~/.codeflow/config.yaml)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def review(project_dir: Path, config: Optional[Path], debug: bool, checkpoint: bool):
    """Review existing files and append feedback to the prompt.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        setup_logging(debug)
        logger.info("Starting review with project directory: %s", project_dir)
        
        # Find and parse codeflow.md
        prompt_file = find_codeflow_file(project_dir)
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed successfully from %s", prompt_file)
        
        # Auto-checkpoint if enabled
        if checkpoint:
            auto_checkpoint(project_dir, "review", prompt)

        # Create session and pipeline
        session, config_data = create_session(config, debug)
        pipeline = ReviewPipeline(session, prompt)
        
        # Execute pipeline
        result = asyncio.run(pipeline.execute())
                
        # Display results
        if result["status"] == "success":
            click.echo(f"Reviewed {len(result.get('files_reviewed', []))} files using team: {', '.join(result.get('team', []))}")
            click.echo("Reviews have been appended to the prompt file.")
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            if debug and 'context' in result:
                click.echo(f"Context: {result['context']}")
        
        logger.info("Review completed with status: %s", result["status"])
        
    except Exception as e:
        logger.error("Review failed: %s", str(e), exc_info=debug)
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(path_type=Path))
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def init(project_dir: Path, checkpoint: bool):
    """Initialize a new codeflow project directory.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    logger.info("Initializing new codeflow project in: %s", project_dir)
    
    prompt_path = project_dir / "codeflow.md"
    if prompt_path.exists():
        click.echo(f"codeflow.md already exists at {prompt_path}")
        return

    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
    
    template = """# New Project

## Goal
Describe what needs to be built here.

## Output
src/file1.py
src/file2.py

## Context
.

## Team
maya
merlin
"""
    # Auto-checkpoint if enabled and in a git repo
    if checkpoint:
        # Load an empty config
        config_data = {}
        auto_checkpoint(project_dir, "init", {"files": ["codeflow.md"]})

    prompt_path.write_text(template)
    logger.info("Created new codeflow file at: %s", prompt_path)
    click.echo(f"Created new codeflow project in {project_dir}")
    click.echo(f"Created codeflow.md configuration file at {prompt_path}")
    
    # Create src directory
    src_dir = project_dir / "src"
    src_dir.mkdir(exist_ok=True)
    click.echo(f"Created src directory at {src_dir}")
    

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
def rebase(project_dir: Path):
    """Rebase to before codeflow checkpoints.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        logger.info("Looking for last non-codeflow commit")
        
        # Find the last non-codeflow commit
        commit_hash = find_last_non_codeflow_commit(project_dir)
        if not commit_hash:
            click.echo("No non-codeflow commits found. Repository may be new or completely made with codeflow.")
            return
            
        # Confirm with user
        click.echo(f"Found last non-codeflow commit: {commit_hash[:8]}")
        if not click.confirm("Rebase to this commit? This will remove all codeflow checkpoint commits but preserve your changes."):
            click.echo("Rebase cancelled.")
            return
            
        # Perform the rebase
        if rebase_to_commit(project_dir, commit_hash):
            click.echo(f"Successfully rebased to commit {commit_hash[:8]}")
            click.echo("All codeflow checkpoint commits have been squashed, but your changes are preserved.")
        else:
            click.echo("Rebase failed. You may need to resolve conflicts manually.")
            
    except Exception as e:
        logger.error(f"Rebase failed: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
