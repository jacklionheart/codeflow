# loopflow/cli/loopflow.py
"""
Command-line interface for loopflow.

This module provides the main entry points for running loopflow from the
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

from loopflow.io.session import Session, Config, CLIUser
from loopflow.compose.prompt import Prompt
from loopflow.compose.pipeline import (
    ClarifyPipeline, 
    MatePipeline, 
    TeamPipeline, 
    ReviewPipeline,
)
from loopflow.io.git import auto_checkpoint, find_last_non_loopflow_commit, rebase_to_commit

logger = logging.getLogger("loopflow.cli")

class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass

class ProjectError(Exception):
    """Exception raised for project structure errors."""
    pass

def find_loopflow_file(project_dir: Path) -> Path:
    """
    Find the loopflow.md file in the project directory.
    
    Args:
        project_dir: Directory to search in
        
    Returns:
        Path to the loopflow.md file
        
    Raises:
        ProjectError: If loopflow.md file is not found
    """
    loopflow_file = project_dir / "loopflow.md"
    
    if not loopflow_file.exists():
        raise ProjectError(
            f"loopflow.md not found in {project_dir}. "
            f"Run 'loopflow init {project_dir}' to create a new project."
        )
    
    return loopflow_file

def setup_logging(debug: bool) -> None:
    """Configure logging with appropriate level and format."""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger().setLevel(logging.INFO)
    logger = logging.getLogger("loopflow")
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
    """Loopflow - Orchestrate LLM collaboration for file generation."""
    pass

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to config file (default: ~/.loopflow/config.yaml)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def clarify(project_dir: Path, config: Optional[Path], debug: bool, checkpoint: bool):
    """Generate questions to clarify requirements.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        setup_logging(debug)
        logger.info("Starting clarify with project directory: %s", project_dir)
        
        # Find and parse loopflow.md
        prompt_file = find_loopflow_file(project_dir)
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed successfully from %s", prompt_file)
        
        # Create session and pipeline
        session, config_data = create_session(config, debug)
        pipeline = ClarifyPipeline(session, prompt)
        
        # Auto-checkpoint if enabled
        if checkpoint:
            details = {
                "questions": len(result.get("questions", {}))
            }
            auto_checkpoint(project_dir, "clarify", details)

        # Execute pipeline
        result = asyncio.run(pipeline.execute())
                
        # Display results
        if result["status"] == "success":
            click.echo("Questions have been appended to the prompt file.")
            click.echo("Please add your answers and then run 'loopflow team' or 'loopflow mate'.")
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
              help='Path to config file (default: ~/.loopflow/config.yaml)')
@click.option('--mate', '-m', help='Specific mate to use (default: first mate in prompt)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def mate(project_dir: Path, config: Optional[Path], mate: Optional[str], debug: bool, checkpoint: bool):
    """Generate drafts with a specific mate.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        setup_logging(debug)
        logger.info("Starting mate with project directory: %s", project_dir)
        
        # Find and parse loopflow.md
        prompt_file = find_loopflow_file(project_dir)
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed successfully from %s", prompt_file)
        
        # Auto-checkpoint if enabled
        if checkpoint:
            details = {
                "mate": result.get("mate", "unknown"),
                "files": len(result.get("outputs", {}))
            }
            auto_checkpoint(project_dir, "mate", details)
        
        # Create session and pipeline
        session, config_data = create_session(config, debug)
        pipeline = MatePipeline(session, prompt, mate_name=mate)
        
        # Execute pipeline
        result = asyncio.run(pipeline.execute())
                
        # Display results
        if result["status"] == "success":
            click.echo(f"Generated {len(result.get('outputs', {}))} files with mate: {result.get('mate', 'unknown')}")
            for path, content in result.get('outputs', {}).items():
                click.echo(f"  - {path}: {len(content)} chars")
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            if debug and 'context' in result:
                click.echo(f"Context: {result['context']}")
        
        logger.info("Mate completed with status: %s", result["status"])
        
    except Exception as e:
        logger.error("Mate failed: %s", str(e), exc_info=debug)
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to config file (default: ~/.loopflow/config.yaml)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def team(project_dir: Path, config: Optional[Path], debug: bool, checkpoint: bool):
    """Run the full team workflow (draft, review, synthesize).
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        setup_logging(debug)
        logger.info("Starting team workflow with project directory: %s", project_dir)
        
        # Find and parse loopflow.md
        prompt_file = find_loopflow_file(project_dir)
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed successfully from %s", prompt_file)
        
        # Auto-checkpoint if enabled
        if checkpoint:
            details = {
                "team": ",".join(result.get("team", [])),
                "files": len(result.get("outputs", {}))
            }
            auto_checkpoint(project_dir, "team", details)

        # Create session and pipeline
        session, config_data = create_session(config, debug)
        pipeline = TeamPipeline(session, prompt)
        
        # Execute pipeline
        result = asyncio.run(pipeline.execute())
                
        # Display results
        if result["status"] == "success":
            click.echo(f"Generated {len(result.get('outputs', {}))} files using team: {', '.join(result.get('team', []))}")
            for path, _ in result.get('outputs', {}).items():
                click.echo(f"  - {path}")
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            if debug and 'context' in result:
                click.echo(f"Context: {result['context']}")
        
        logger.info("Team workflow completed with status: %s", result["status"])
        
    except Exception as e:
        logger.error("Team workflow failed: %s", str(e), exc_info=debug)
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to config file (default: ~/.loopflow/config.yaml)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
@click.option('--checkpoint/--no-checkpoint', default=True, help='Enable/disable auto git checkpointing')
def review(project_dir: Path, config: Optional[Path], debug: bool, checkpoint: bool):
    """Review existing files and append feedback to the prompt.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        setup_logging(debug)
        logger.info("Starting review with project directory: %s", project_dir)
        
        # Find and parse loopflow.md
        prompt_file = find_loopflow_file(project_dir)
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed successfully from %s", prompt_file)
        
        # Auto-checkpoint if enabled
        if checkpoint:
            details = {
                "team": ",".join(result.get("team", [])),
                "files_reviewed": len(result.get("files_reviewed", []))
            }
            auto_checkpoint(project_dir, "review", details)

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
    """Initialize a new loopflow project directory.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    logger.info("Initializing new loopflow project in: %s", project_dir)
    
    project_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = project_dir / "loopflow.md"
    
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
    
    prompt_path.write_text(template)
    logger.info("Created new loopflow file at: %s", prompt_path)
    click.echo(f"Created new loopflow project in {project_dir}")
    click.echo(f"Created loopflow.md configuration file at {prompt_path}")
    
    # Create src directory
    src_dir = project_dir / "src"
    src_dir.mkdir(exist_ok=True)
    click.echo(f"Created src directory at {src_dir}")
    
    # Auto-checkpoint if enabled and in a git repo
    if checkpoint:
        # Load an empty config
        config_data = {}
        auto_checkpoint(project_dir, "init", {"files": ["loopflow.md"]})

@cli.command()
@click.argument('project_dir', required=False, default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
def rebase(project_dir: Path):
    """Rebase to before loopflow checkpoints.
    
    If PROJECT_DIR is omitted, the current directory (".") is used.
    """
    try:
        logger.info("Looking for last non-loopflow commit")
        
        # Find the last non-loopflow commit
        commit_hash = find_last_non_loopflow_commit(project_dir)
        if not commit_hash:
            click.echo("No non-loopflow commits found. Repository may be new or completely made with loopflow.")
            return
            
        # Confirm with user
        click.echo(f"Found last non-loopflow commit: {commit_hash[:8]}")
        if not click.confirm("Rebase to this commit? This will remove all loopflow checkpoint commits but preserve your changes."):
            click.echo("Rebase cancelled.")
            return
            
        # Perform the rebase
        if rebase_to_commit(project_dir, commit_hash):
            click.echo(f"Successfully rebased to commit {commit_hash[:8]}")
            click.echo("All loopflow checkpoint commits have been squashed, but your changes are preserved.")
        else:
            click.echo("Rebase failed. You may need to resolve conflicts manually.")
            
    except Exception as e:
        logger.error(f"Rebase failed: {str(e)}")
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
