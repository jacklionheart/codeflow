# llm.py
"""
Core abstractions for LLM interactions in codeflow.

This module provides the base interfaces and data structures for working with
large language models, with each LLM instance representing a single conversation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Tuple

class LLMError(Exception):
    """Raised when LLM operations fail."""
    pass

@dataclass
class UsageStats:
    """
    Tracks token usage and associated costs.
    
    Attributes:
        input_tokens: Total tokens in prompts
        output_tokens: Total tokens in completions
    """    
    # TODO: This isnt working
    usd_per_1000_input_tokens: float = 0.003
    usd_per_1000_output_tokens: float = 0.015
    input_tokens: int = 0
    output_tokens: int = 0

    def total_cost(self) -> float:
        return self.input_cost_usd() + self.output_cost_usd()
    
    def input_cost_usd(self) -> float:
        """Cost in USD for input tokens."""
        return self.input_tokens * self.usd_per_1000_input_tokens / 1000
    
    def output_cost_usd(self) -> float:
        """Cost in USD for output tokens."""
        return self.output_tokens * self.usd_per_1000_output_tokens / 1000

    def track(self, input_tokens: int, output_tokens: int) -> None:
        """Record usage from a single interaction."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

@dataclass
class Interaction:
    """A single prompt --> response interaction."""
    prompt: str
    response: str

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Providers handle authentication and client setup, while delegating
    actual chat interactions to model instances.
    """
    usage: UsageStats
    def track(self, input_tokens: int, output_tokens: int) -> None:
        """Record usage from a single interaction."""
        self.usage.track(input_tokens, output_tokens)

    @abstractmethod
    def createLLM(self, name: str, system_prompt: str) -> "LLM":
        """Create a new model instance."""
        pass


class LLM(ABC):
    """
    Abstract base class for language models.
    
    Each instance represents a single conversation thread, maintaining
    context between chat calls.
    """

    name: str
    system_prompt: str
    provider: LLMProvider
    
    def __init__(self, name: str, provider: LLMProvider, system_prompt: str):
        """
        Initialize a model instance.
        
        Args:
            provider: The authenticated provider to use
        """
        self.name = name
        self.provider = provider
        self.history: List[Interaction] = []
        self.system_prompt = system_prompt
    async def chat(self, prompt: str, include_history: bool = False) -> str:
        """
        Send a message and get a response, maintaining conversation context.
        
        Args:
            prompt: The user's input message
            
        Returns:
            The model's response
            
        Raises:
            LLMError: If the chat interaction fails
        """

        messages = []
        if include_history:
            for interaction in self.history:
                messages.append({"role": "user", "content": interaction.prompt})
                messages.append({"role": "assistant", "content": interaction.response})
        messages.append({"role": "user", "content": prompt})
            
        interaction = Interaction(prompt=prompt, response="")
        response, input_tokens, output_tokens = await self._chat(messages)
        interaction.response = response

        self.provider.track(input_tokens, output_tokens)
        self.history.append(interaction)
        return response
    
    @abstractmethod
    async def _chat(self, prompt: str) -> Tuple[str, int, int]:
        """
        Execute the actual chat interaction.
        
        Concrete implementations should focus only on the API interaction,
        as history management is handled by the base class.
        
        Args:
            prompt: The user's input message
            
        Returns:
            The model's response
            Input tokens used
            Output tokens used
            
        Raises:
            LLMError: If the chat interaction fails
        """
        pass


