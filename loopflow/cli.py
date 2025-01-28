"""
Command-line interface for loopflow.

This module provides the main entry points for running loopflow from the
command line. It handles command parsing, configuration loading, and
execution setup while delegating the actual work to the Session class.
"""

import asyncio
from pathlib import Path
import yaml
import click
from typing import Optional, Dict, Any

from .prompt import Prompt
from .llm import LLMProvider, Anthropic, LLM
from .session import Session, User
from .templates import load_all_teammates

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
    
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    
    try:
        config = yaml.safe_load(path.read_text())
                    
        return config
        
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}")

def setup_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Create an LLM provider from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured LLM provider
        
    Raises:
        LoopflowError: If provider configuration is invalid
    """

    # Validate required sections
    if "accounts" not in config:
        raise ConfigError("Missing 'accounts' section in config")
    # For now, require Anthropic
    if "anthropic" in config["accounts"]:
        return Anthropic(config["accounts"]["anthropic"])
    else:
        raise ConfigError("No valid LLM provider configured")

def load_llms(provider: LLMProvider, teammates: Dict[str, Any]) -> Dict[str, LLM]:
    llms = {}
    for name, mate in load_all_teammates():
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
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def run(prompt_file: Path, config: Optional[Path], verbose: bool):
    """Run a loopflow prompt file."""
    try:
        # Parse prompt and configuration
        prompt = Prompt.from_file(prompt_file)
        prompt.validate()
        
        config_data = load_config(config)
        provider = setup_provider(config_data)
        
        if verbose:
            click.echo(f"Parsed prompt from {prompt_file}")
            click.echo(f"Goal: {prompt.goal}")
            click.echo(f"Output files: {', '.join(prompt.output_files)}")
            if prompt.context_files:
                click.echo(f"Context files: {', '.join(prompt.context_files)}")
        
        # Create and run session
        user = User()
        session = Session(user, provider)
        result = asyncio.run(session.run(prompt))
        
        if verbose:
            click.echo("\nExecution complete:")
            click.echo(f"Duration: {result['execution_time']:.1f}s")
            click.echo(f"Files generated: {result['metrics']['file_count']}")
            click.echo(f"Total cost: ${result['usage'].get('total_cost_usd', 0):.4f}")
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('output_dir', type=click.Path(path_type=Path))
def init(output_dir: Path):
    """Initialize a new loopflow prompt file."""
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

## Reviewers
- ML Researcher
- Engineer
"""
    
    prompt_path.write_text(template)
    click.echo(f"Created new prompt file at {prompt_path}")

if __name__ == '__main__':
    cli()