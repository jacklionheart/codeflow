"""
Command-line interface for code context retrieval.

Provides a flexible way to extract context from codebases for LLM interactions.
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple
from loopflow.compose.file import get_context

import click


def copy_to_clipboard(content: str) -> None:
    """Copy content to clipboard on macOS."""
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(content.encode('utf-8'))
    except FileNotFoundError:
        click.echo("pbcopy not found - clipboard integration skipped", err=True)

@click.command()
@click.argument('paths')
@click.option('-p', '--pbcopy', is_flag=True, help="Copy to clipboard (macOS only)")
@click.option('-r', '--raw', is_flag=True, help="Output in raw format instead of XML")
@click.option('-e', '--extension', multiple=True, help="File extensions to include (e.g. -e .py -e .js)")
def cli(paths: str, pbcopy: bool, raw: bool, extension: Tuple[str, ...]) -> None:
    """
    Provide codebase context to LLMs with smart defaults.
    - PATHS can be comma-separated. Example: "manabot,managym/tests"
    """
    # Split and clean paths
    path_list = [path.strip() for path in paths.split(',')]
    
    # Load context documents using the default root (~/src)
    try:
        output_content = get_context(
            paths=path_list,
            raw=raw,
            extensions=extension
        )
    except Exception as e:
        click.echo(f"Error loading context: {e}", err=True)
        return

    if pbcopy:
        copy_to_clipboard(output_content)
    else:
        click.echo(output_content)