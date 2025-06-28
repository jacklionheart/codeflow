"""Mock implementations for testing the LLM infrastructure."""

from collections import deque
from typing import Dict, Any, Optional, List, Tuple
import asyncio
from unittest.mock import AsyncMock, MagicMock

from codeflow.llm import LLM, UsageStats, LLMProvider

class MockLLM(LLM):
    """A mock LLM for testing."""
    def __init__(self, name: str, provider: 'MockProvider' = None, system_prompt: str = ""):
        super().__init__(name, provider or MockProvider(), system_prompt)
        self.responses: deque[str | Exception] = deque()
        self.calls: List[str] = []
    
    def queue_response(self, response: str | Exception) -> None:
        """Add a response to return on next chat."""
        self.responses.append(response)
    
    async def _chat(self, prompt: str) -> Tuple[str, int, int]:
        """Mock chat implementation that returns queued responses."""
        self.calls.append(prompt)
        
        if self.responses:
            response = self.responses.popleft()
            if isinstance(response, Exception):
                raise response
            return response, 10, 20  # Fixed token counts for testing
        
        return "Mock response", 10, 20

class MockProvider(LLMProvider):
    """A provider that creates mock LLMs."""
    def __init__(self):
        self.usage = UsageStats(0, 0)
        self.llms: Dict[str, MockLLM] = {}
        
    def createLLM(self, name: str, system_prompt: str = None) -> MockLLM:
        """Create a new mock LLM."""
        llm = MockLLM(name, self, system_prompt)
        self.llms[name] = llm
        return llm

class MockUser:
    """A mock user that returns predefined responses."""
    def __init__(self, responses=None):
        self.name = "test_user"
        self.responses = responses or ["Test user response"]
        self.current = 0
    
    async def chat(self, prompt: str) -> str:
        if self.current < len(self.responses):
            response = self.responses[self.current]
            self.current += 1
            return response
        return self.responses[-1]