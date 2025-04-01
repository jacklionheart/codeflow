"""
prompt.py
Parsing user prompt markdown files
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional   
import loopflow.io.file

class PromptError(Exception):
    """Exception raised for errors in the prompt file."""
    pass

# Update prompt.py to add validation and path handling:

class Prompt:
    """Represents a parsed loopflow prompt file."""
    def __init__(
        self, 
        path: Path,
        goal: str,
        output_files: List[str | Path],
        team: List[str],
        context_files: Optional[List[str | Path]] = None
    ):
        # Validate inputs
        if not goal or not goal.strip():
            raise PromptError("Goal cannot be empty")
        if not output_files:
            raise PromptError("At least one output file is required")

        self.goal = goal.strip()
        self.path = path
        self.project_dir = path.parent
            
        # Resolve output file paths
        try:
            self.output_files = [
                loopflow.io.file.resolve_codebase_path(p, project_dir=self.project_dir, for_reading=False) 
                for p in output_files
            ]
        except ValueError as e:
            raise PromptError(f"Invalid output path: {e}")
            
        # Resolve context file paths
        self.context_files = None
        if context_files:
            try:
                self.context_files = [
                    loopflow.io.file.resolve_codebase_path(p, project_dir=self.project_dir, for_reading=True)
                    for p in context_files
                ]
            except ValueError as e:
                raise PromptError(f"Invalid context path: {e}")
        
        # Clean team member list
        self.team = []
        for member in team:
            # Strip bullets and whitespace
            cleaned = member.strip()
            cleaned = cleaned.lstrip('-').strip()
            cleaned = cleaned.lstrip('*').strip()
            if cleaned:
                self.team.append(cleaned)
        if not self.team:
            raise PromptError("At least one team member is required")

    @classmethod
    def from_file(cls, path: Path) -> 'Prompt':
        """Create a prompt instance from a markdown file."""
        try:
            sections = cls._parse_sections(path.read_text())
            
            # Basic validation
            if sections.get('Goal', '').strip() == '':
                raise PromptError("Goal section is required")
            if sections.get('Output', '').strip() == '':
                raise PromptError("Output section is required")

            # Parse sections
            output_files = [
                f.strip() for f in sections['Output'].split('\n')
                if f.strip()
            ]
            
            context_files = None
            if 'Context' in sections:
                context_files = []
                for line in sections['Context'].split('\n'):
                    context_files.extend(
                        f.strip()
                        for f in line.split(',')
                        if f.strip()
                    )
            team = ['maya', 'merlin']
            if 'Team' in sections:
                team = [
                    line.strip()
                    for line in sections['Team'].split('\n')
                    if line.strip() and line.strip() != 'Team'
                ]
            
            # Create instance
            return cls(
                path=path,
                goal=sections['Goal'].strip(),
                output_files=output_files,
                team=team,
                context_files=context_files
            )
        except Exception as e:
            if isinstance(e, PromptError):
                raise
            raise PromptError(f"Failed to parse prompt file: {e}")

    @staticmethod
    def _parse_sections(content: str) -> dict[str, str]:
        """Parse markdown sections into a dictionary."""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections
