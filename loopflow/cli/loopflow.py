# loopflow/cli/loopflow.py
"""
Command-line interface for loopflow.

This module provides the main entry points for running loopflow from the
command line. It handles command parsing, configuration loading, and
execution setup while delegating the actual work to the Session class.
"""

import asyncio
import logging
from pathlib import Path
import yaml
import click
from typing import Optional, Dict, Any

from loopflow.prompt import Prompt
from loopflow.llm import LLMProvider, Anthropic, LLM
from loopflow.session import Session, User
from loopflow.templates import load_all_teammates

logger = logging.getLogger("loopflow.cli")

class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass

def load_config(path: Optional[Path]) -> Dict[str, Any]:
    """
    Load and validate configuration from file.
    
    Args:
        path: Path to config file, or None for default location
        
    Returns:
        Parsed configuration dictionary
        
    Raises:
        ConfigError: If config is missing or invalid
    """
    # Use default config path if none provided
    if not path:
        path = Path.home() / "loopflow" / "config.yaml"
    
    logger.debug("Loading config from: %s", path)
    
    if not path.exists():
        logger.error("Config file not found: %s", path)
        raise ConfigError(f"Config file not found: {path}")
    
    try:
        config = yaml.safe_load(path.read_text())
        logger.debug("Config loaded successfully")
        return config
        
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        raise ConfigError(f"Failed to load config: {e}")

def setup_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Create an LLM provider from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured LLM provider
        
    Raises:
        ConfigError: If provider configuration is invalid
    """
    logger.debug("Setting up LLM provider")

    # Validate required sections
    if "accounts" not in config:
        logger.error("Missing 'accounts' section in config")
        raise ConfigError("Missing 'accounts' section in config")

    # For now, require Anthropic
    if "anthropic" in config["accounts"]:
        logger.info("Creating Anthropic provider")
        return Anthropic(config["accounts"]["anthropic"])
    else:
        logger.error("No valid LLM provider configured")
        raise ConfigError("No valid LLM provider configured")

def load_llms(provider: LLMProvider, teammates: Dict[str, Any]) -> Dict[str, LLM]:
    logger.debug("Loading LLMs for team members: %s", list(teammates.keys()))
    llms = {}
    for name, mate in teammates.items():
        logger.debug("Creating LLM for team member: %s", name)
        llms[name] = provider.createLLM(
            name=name,
            system_prompt=mate.system_prompt,
            priorities=mate.priorities
        )
    return llms

@click.group()
def cli():
    """Loopflow - Orchestrate LLM collaboration for file generation."""
    pass

@cli.command()
@click.argument('prompt_file', type=click.Path(exists=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to config file (default: ~/.loopflow/config.yaml)')
@click.option('--debug', '-d', is_flag=True, help='Enable debug logging')
def run(prompt_file: Path, config: Optional[Path], debug: bool):
    """Run a loopflow prompt file."""
    try:
        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.getLogger().setLevel(logging.INFO)
        logger = logging.getLogger("loopflow")
        logger.setLevel(log_level)
        
        logger.info("Starting loopflow run with prompt file: %s", prompt_file)
        
        # Parse prompt and configuration
        prompt = Prompt.from_file(prompt_file)
        logger.info("Prompt parsed and validated successfully")
        
        config_data = load_config(config)
        provider = setup_provider(config_data)
        
        if debug:
            click.echo(f"Parsed prompt from {prompt_file}")
            click.echo(f"Goal: {prompt.goal}")
            click.echo(f"Output files: {', '.join(map(str, prompt.output_files))}")
            if prompt.context_files:
                click.echo(f"Context files: {', '.join(map(str, prompt.context_files))}")
        
        # Create and run session
        user = User()
        logger.debug("Loading team members")
        teammates = load_all_teammates()
        
        logger.info("Creating session")
        session = Session(
            user=user,
            available_llms=load_llms(provider, teammates),
            provider=provider
        )
        
        logger.info("Running session")
        result = asyncio.run(session.run(prompt))
        
        if debug:
            click.echo("\nExecution complete:")
            click.echo(f"Duration: {result['execution_time']:.1f}s")
            click.echo(f"Files generated: {result['metrics']['file_count']}")
            click.echo(f"Total cost: ${result['usage'].totalCostUsd():.4f}")
        
        logger.info("Run completed successfully")
            
    except Exception as e:
        logger.error("Run failed: %s", str(e), exc_info=debug)
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('output_dir', type=click.Path(path_type=Path))
def init(output_dir: Path):
    """Initialize a new loopflow prompt file."""
    logger.info("Initializing new prompt file in: %s", output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "prompt.md"
    
    template = """# New Project

## Goal
Describe what needs to be built here.

## Output
output/file1.py
output/file2.py

## Context
context_dir

## Team
- ML Researcher
- Engineer
"""
    
    prompt_path.write_text(template)
    logger.info("Created new prompt file at: %s", prompt_path)
    click.echo(f"Created new prompt file at {prompt_path}")

if __name__ == '__main__':
    cli()