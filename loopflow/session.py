"""
Session implementation for loopflow.

The Session class provides a shared environment for both the chat server
and composer CLI, handling provider setup, team management, and basic 
configuration. This serves as the core object shared across different
loopflow applications.
"""

import asyncio
import logging
import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any, List, Union

from loopflow.llm import LLMProvider, LLM, Anthropic, OpenAI
from loopflow.edit.team import Team
from loopflow.templates import load_all_teammates

logger = logging.getLogger(__name__)

class SessionError(Exception):
    """
    Raised when session-level operations fail.
    
    Includes context about what the session was trying to do and relevant
    metrics at the time of failure for debugging and monitoring.
    """
    def __init__(self, message: str, context: Dict[str, Any]):
        self.context = context
        super().__init__(f"Session failed: {message}")

class User:
    """
    Represents the human user interacting with the session.
    
    This base class handles CLI interactions. It can be extended to support 
    other interfaces like Discord.
    """
    def __init__(self, name: str = "user"):
        self.name = name
        self.logger = logging.getLogger(__name__).getChild("user")

    async def chat(self, prompt: str) -> str:
        """
        Chat with the user and return their response.
        
        This implementation uses the CLI for interaction.
        
        Args:
            prompt: The prompt to show to the user
            
        Returns:
            The user's response text
        """
        self.logger.info("Requesting user input")
        self.logger.debug("User prompt: %s", prompt)
        print("\n" + prompt + "\n")
        response = input("Your response: ")
        self.logger.debug("User response: %s", response)
        return response
    
    async def show_message(self, message: str) -> None:
        """
        Display a message to the user without expecting a response.
        
        Args:
            message: The message to display
        """
        print("\n" + message + "\n")

@dataclass
class Config:
    """Configuration for loopflow session."""
    config_path: Optional[Path] = None
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    debug: bool = False
    timeout: float = 300.0

class Session:
    """
    Core session object shared by both chat server and composer CLI.
    
    Handles provider setup, team management, and configuration loading.
    """
    
    def __init__(
        self,
        user: User,
        config: Optional[Config] = None,
    ):
        """
        Initialize session with its configuration.
        
        Args:
            user: The user interacting with the session
            config: Configuration options (optional)
        """
        self.user = user
        self.config = config or Config()
        self.logger = logging.getLogger("loopflow.session")
        self.providers: Dict[str, LLMProvider] = {}
        self.available_llms: Dict[str, LLM] = {}
        self.timeout = self.config.timeout
        
        # Set up immediately
        self._setup_providers()
        self._load_teammates()
        
        self.logger.info("Session initialized with %d providers and %d LLMs", 
                         len(self.providers), len(self.available_llms))

    def _setup_providers(self) -> None:
        """Set up LLM providers based on configuration and environment."""
        self.logger.debug("Setting up LLM providers")
        
        # First check config object
        if self.config.anthropic_api_key:
            self._add_anthropic_provider(self.config.anthropic_api_key)
        
        if self.config.openai_api_key:
            self._add_openai_provider(self.config.openai_api_key)
        
        # Then check environment variables
        if "ANTHROPIC_API_KEY" in os.environ and "anthropic" not in self.providers:
            self._add_anthropic_provider(os.environ["ANTHROPIC_API_KEY"])
            
        if "OPENAI_API_KEY" in os.environ and "openai" not in self.providers:
            self._add_openai_provider(os.environ["OPENAI_API_KEY"])
        
        # Finally check config file
        if self.config.config_path and self.config.config_path.exists():
            self._load_config_file()
        else:
            # Try default location
            default_config = Path.home() / ".loopflow" / "config.yaml"
            if default_config.exists():
                self._load_config_file(default_config)
        
        if not self.providers:
            self.logger.error("No valid LLM providers found")
            raise SessionError("No valid LLM provider configured", {})
    
    def _add_anthropic_provider(self, api_key: str) -> None:
        """Add Anthropic provider with the given API key."""
        self.logger.info("Creating Anthropic provider")
        config = {"api_key": api_key}
        self.providers["anthropic"] = Anthropic(config)
    
    def _add_openai_provider(self, api_key: str) -> None:
        """Add OpenAI provider with the given API key."""
        self.logger.info("Creating OpenAI provider")
        config = {"api_key": api_key}
        self.providers["openai"] = OpenAI(config)
    
    def _load_config_file(self, config_path: Optional[Path] = None) -> None:
        """Load configuration from YAML file."""
        path = config_path or self.config.config_path
        if not path:
            return
        
        self.logger.info(f"Loading config from {path}")
        try:
            with open(path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or not isinstance(config_data, dict):
                self.logger.warning(f"Invalid config format in {path}")
                return
            
            # Load accounts section
            accounts = config_data.get('accounts', {})
            
            # Anthropic
            if 'anthropic' in accounts and 'api_key' in accounts['anthropic']:
                if 'anthropic' not in self.providers:
                    self._add_anthropic_provider(accounts['anthropic']['api_key'])
            
            # OpenAI
            if 'openai' in accounts and 'api_key' in accounts['openai']:
                if 'openai' not in self.providers:
                    self._add_openai_provider(accounts['openai']['api_key'])
                    
        except Exception as e:
            self.logger.error(f"Error loading config file: {e}")
    
    def _load_teammates(self) -> None:
        """Load all teammate configurations and create LLMs."""
        self.logger.debug("Loading teammate configurations")
        
        # Load teammate definitions
        teammates = load_all_teammates()
        self.logger.info(f"Loaded {len(teammates)} teammate configurations")
        
        # Create LLMs for each teammate
        for name, config in teammates.items():
            provider_name = config.provider
            
            if provider_name not in self.providers:
                self.logger.warning(f"Skipping mate {name}: provider {provider_name} not available")
                continue
            
            provider = self.providers[provider_name]
            llm = provider.createLLM(
                name=name,
                system_prompt=config.system_prompt
            )
            
            self.available_llms[name] = llm
            self.logger.debug(f"Created LLM for teammate: {name}")
    
    def setup_team(self, team_names: List[str]) -> Team:
        """
        Create a Team object with the specified team members.
        
        Args:
            team_names: List of team member names to include
            
        Returns:
            Team instance with the requested members
            
        Raises:
            SessionError: If any requested team member isn't available
        """
        self.logger.debug(f"Setting up team with members: {team_names}")
        llms = {}
        missing = []
        
        for name in team_names:
            if name not in self.available_llms:
                missing.append(name)
                continue
            llms[name] = self.available_llms[name]
        
        if missing:
            self.logger.error(f"Unknown team members requested: {missing}")
            available = list(self.available_llms.keys())
            self.logger.error(f"Available team members: {available}")
            raise SessionError(
                f"Unknown team members: {', '.join(missing)}",
                {"requested": team_names, "available": available}
            )
        
        return Team(self.providers, llms)
    
    def get_llm(self, name: str) -> LLM:
        """
        Get a specific LLM by name.
        
        Args:
            name: Name of the LLM to retrieve
            
        Returns:
            The requested LLM
            
        Raises:
            SessionError: If the requested LLM isn't available
        """
        if name not in self.available_llms:
            raise SessionError(
                f"Unknown LLM: {name}",
                {"available": list(self.available_llms.keys())}
            )
        
        return self.available_llms[name]
    
    def total_cost(self) -> float:
        """Calculate the total cost of LLM usage in this session."""
        return sum(provider.usage.total_cost() for provider in self.providers.values())