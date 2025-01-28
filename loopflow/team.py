import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from loopflow.llm import LLM


class Team:
    """
    A set of LLMs used to execute jobs.
    """
    
    def __init__(self, llms: Dict[str, LLM]):
        self.llms = llms

    def priorities(self, name: str) -> str:
        return self.configs[name].priorities
    
    async def query_parallel(self, prompt_template: str, args: Dict[str, Any]) -> Dict[str, str]:
        tasks = []
        mate_names = []
        
        for name, llm in self.llms.items():
            prompt = prompt_template.format(name=name, **args)
            # Create the coroutine but don't await it yet
            tasks.append(asyncio.create_task(llm.chat(prompt)))
            mate_names.append(name)
        
        # Now await all tasks together
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for name, response in zip(mate_names, responses):
            if isinstance(response, Exception):
                results[name] = f"Error: {str(response)}"
            else:
                results[name] = response
        
        return results


class MateError(Exception):
    """Raised when team member configuration is invalid."""
    pass

@dataclass
class MateConfig:
    """
    Represents a team member persona/role in the workflow.
    
    Each team member has a specific focus area and system prompt that guides
    their contributions to the generation process.
    
    Attributes:
        name: Identifier for this team member
        priorities: List of priorities this member specializes in
        system_prompt: The system prompt to use when creating this member's LLM
    """
    name: str
    priorities: str
    system_prompt: str
    
    @classmethod
    def from_file(cls, path: Path) -> 'MateConfig':
        """
        Create a MateConfig from a markdown file.
        
        The file should have sections for System Prompt,
        and and Priorities.
        
        Args:
            path: Path to the markdown file
            
        Returns:
            Configured MateConfig instance
            
        Raises:
            MateError: If file is missing or has invalid format
        """
        try:
            content = path.read_text()
            sections = cls._parse_sections(content)
            
            # Required sections
            if 'Priorities' not in sections:
                raise MateError("Member file missing Priorities section")
            if 'System Prompt' not in sections:
                raise MateError("Member file missing System Prompt section")
                
            return cls(
                name=path.stem,  # Use filename as identifier
                priorities=sections['Priorities'].strip(),
                system_prompt=sections['System Prompt'].strip(),
            )
            
        except Exception as e:
            if isinstance(e, MateError):
                raise
            raise MateError(f"Failed to parse member file: {e}")
    
    @staticmethod
    def _parse_sections(content: str) -> Dict[str, str]:
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