"""
Template and team member management for codeflow.

This module provides access to both prompt templates and team member
configurations used throughout the workflow. Templates and member configs
are stored as markdown files in their respective directories and are
loaded automatically when the module is imported.
"""

import importlib.resources
from pathlib import Path
from typing import Dict, List

from codeflow.llm.mate import MateConfig

def load_resource(category: str, name: str) -> str:
    """
    Load a resource (template or member config) from the appropriate directory.
    
    Args:
        category: Either 'jobs' or 'mates'
        name: Resource name without .md extension
        
    Returns:
        Resource content as string
        
    Raises:
        FileNotFoundError: If resource doesn't exist or can't be read
    """
    try:
        # Use __package__ to reference our own package
        with importlib.resources.files(__package__).joinpath(f"{category}/{name}.md").open('r') as f:
            return f.read()
    except Exception as e:
        raise FileNotFoundError(f"Failed to load {category}/{name}: {e}")

def load_all_teammates() -> Dict[str, MateConfig]:
    """
    Load all team member configurations from the members directory.
    
    Returns:
        Dictionary mapping member names to MateConfig instances
    """
    teammates = {}
    member_dir = importlib.resources.files(__package__).joinpath('mates')
    
    for path in member_dir.glob('*.md'):
        teammate = MateConfig.from_file(path)

        if teammate.name in teammates:
            raise ValueError(f"Duplicate teammate name: {teammate.name}")
        teammates[teammate.name] = teammate
            
    return teammates

# Load all standard resources at module initialization
QUESTION_TEMPLATE = load_resource('jobs', 'clarify')
DRAFT_TEMPLATE = load_resource('jobs', 'draft')
REVIEW_TEMPLATE = load_resource('jobs', 'review')
SYNTHESIS_TEMPLATE = load_resource('jobs', 'synthesize')

# Load all team members
TEAMMATES = load_all_teammates()

# Export templates, members, and loader functions
__all__ = [
    'load_resource',
    'load_all_teammates',
    'QUESTION_TEMPLATE',
    'DRAFT_TEMPLATE',
    'REVIEW_TEMPLATE',
    'SYNTHESIS_TEMPLATE',
    'TEAMMATES'
]
