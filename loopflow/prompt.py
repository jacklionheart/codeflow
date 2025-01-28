from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
import yaml
from yaml.parser import ParserError

class PromptError(Exception):
    """Exception raised for errors in the prompt file."""
    pass

@dataclass
class Prompt:
    """Represents a parsed loopflow prompt file."""
    goal: str
    output_files: List[str]
    reviewers: List[str]
    context_files: Optional[List[str]] = None

    @classmethod
    def from_file(cls, path: Path) -> 'Prompt':
        """Create a Prompt instance from a markdown file."""
        try:
            content = path.read_text()
            sections = cls._parse_sections(content)
            return cls(
                goal=sections.get('Goal', '').strip(),
                output_files=cls._parse_output_files(sections.get('Output', '')),
                context_files=cls._parse_context_files(sections.get('Context', '')),
                reviewers=cls._parse_reviewers(sections.get('Reviewers', ''))
            )
        except (IOError, ParserError) as e:
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
    
    @staticmethod
    def _parse_output_files(content: str) -> List[str]:
        """Parse output files section."""
        files = [f.strip() for f in content.split('\n') if f.strip()]
        if not files:
            raise PromptError("At least one output file is required")
        return files


    @staticmethod
    def _parse_context_files(content: str) -> Optional[List[str]]:
        """Parse context files section."""
        if not content:
            return None
        # First split by newlines to get separate lines
        lines = content.split('\n')
        # Then split each line by commas and flatten
        files = []
        for line in lines:
            files.extend(f.strip() for f in line.split(',') if f.strip())
        return files


    @staticmethod
    def _parse_reviewers(content: str) -> List[str]:
        """Parse reviewers section."""
        reviewers = []
        if not content:
            raise PromptError("At least one reviewer is required")  # Changed from "Reviewers section is required"
        
        for line in content.split('\n'):
            if line.strip().startswith('-'):
                reviewer = line.strip()[1:].strip()
                if reviewer:
                    reviewers.append(reviewer)        
        if not reviewers:
            raise PromptError("At least one reviewer is required")
        return reviewers
        
    def validate(self) -> None:
        """Validate the prompt content."""
        if not self.goal:
            raise PromptError("Goal section is required")
        if not self.output_files:
            raise PromptError("At least one output file is required")
        if not self.reviewers:
            raise PromptError("At least one reviewer is required")          

def format_file_list(files: List[str]) -> str:
    """Format a list of files for inclusion in a prompt."""
    return "\n".join(f"- {f}" for f in files)

def format_clarifications(qa_pairs: Dict[str, str]) -> str:
    """Format Q&A pairs for inclusion in a prompt."""
    return "\n\n".join(
        f"Q: {q}\nA: {a}"
        for q, a in qa_pairs.items()
    )

def format_drafts(drafts: Dict[str, str]) -> str:
    """Format multiple code drafts for inclusion in a prompt."""
    return "\n\n".join(
        f"=== {reviewer} Draft ===\n{content}"
        for reviewer, content in drafts.items()
    )

def format_reviews(reviews: List[str]) -> str:
    """Format multiple reviews for inclusion in a prompt."""
    return "\n\n".join(
        f"=== Review {i+1} ===\n{review}"
        for i, review in enumerate(reviews)
    )