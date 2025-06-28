"""
Session implementation for codeflow.

The Session class provides a shared environment for both the chat server
and composer CLI, handling provider setup, team management, and basic 
configuration. This serves as the core object shared across different
codeflow applications.
"""

import asyncio
import logging
import os
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any, List, Callable

from codeflow.llm import LLMProvider, LLM, Anthropic, OpenAI, Team

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

class User(ABC):
    """
    Interface for interacting with users across different platforms.
    
    This abstract base class defines the contract that all user implementations
    must fulfill, allowing for consistent interaction regardless of platform.
    """
    def __init__(self, name: str = "user"):
        self.name = name
        self.logger = logging.getLogger(__name__).getChild("user")
    
    @abstractmethod
    async def chat(self, prompt: str) -> str:
        """
        Chat with the user and return their response.
        
        Args:
            prompt: The prompt to show to the user
            
        Returns:
            The user's response text
        """
        pass
    
    @abstractmethod
    async def show_message(self, message: str) -> None:
        """
        Display a message to the user without expecting a response.
        
        Args:
            message: The message to display
        """
        pass

class CLIUser(User):
    """Implementation of User interface for command-line interactions."""
    
    async def chat(self, prompt: str) -> str:
        """
        Chat with the user via command line and return their response.
        
        Args:
            prompt: The prompt to show to the user
            
        Returns:
            The user's response text
        """
        self.logger.info("Requesting user input via CLI")
        self.logger.debug("User prompt: %s", prompt)
        print("\n" + prompt + "\n")
        response = input("Your response: ")
        self.logger.debug("User response: %s", response)
        return response
    
    async def show_message(self, message: str) -> None:
        """
        Display a message to the user on the command line.
        
        Args:
            message: The message to display
        """
        print("\n" + message + "\n")

class DiscordUser(User):
    """Implementation of User interface for Discord interactions."""
    
    def __init__(
        self, 
        name: str, 
        channel_id: str, 
        user_id: str, 
        message_callback: Callable[[str, str], Any]
    ):
        """
        Initialize a Discord user.
        
        Args:
            name: User's display name
            channel_id: Discord channel ID for this conversation
            user_id: Discord user ID
            message_callback: Callback function to send messages to Discord
        """
        super().__init__(name)
        self.channel_id = channel_id
        self.user_id = user_id
        self.send_message = message_callback
        self.pending_responses = {}
        self.logger = logging.getLogger(f"codeflow.user.discord.{user_id}")
    
    async def chat(self, prompt: str) -> str:
        """
        Chat with the user via Discord and wait for their response.
        
        This method sends a message to Discord and creates a Future to await
        the user's response. The response will be set when the user replies.
        
        Args:
            prompt: The prompt to show to the user
            
        Returns:
            The user's response text
        """
        self.logger.info(f"Requesting input from Discord user {self.name}")
        
        # Create a future to await the response
        response_future = asyncio.Future()
        self.pending_responses[self.channel_id] = response_future
        
        # Send the message to Discord
        await self.send_message(self.channel_id, prompt)
        
        # Wait for the response (will be set by handle_response)
        try:
            response = await response_future
            self.logger.debug(f"Received response from Discord user: {response[:50]}...")
            return response
        except asyncio.CancelledError:
            self.logger.warning("Request for user input was cancelled")
            if self.channel_id in self.pending_responses:
                del self.pending_responses[self.channel_id]
            raise
    
    async def show_message(self, message: str) -> None:
        """
        Display a message to the user on Discord without expecting a response.
        
        Args:
            message: The message to display
        """
        await self.send_message(self.channel_id, message)
    
    def handle_response(self, channel_id: str, message: str) -> bool:
        """
        Handle an incoming response from Discord.
        
        This method should be called when a message is received from the user
        that might be a response to a pending chat request.
        
        Args:
            channel_id: Discord channel ID where the message was sent
            message: The message content
            
        Returns:
            True if this message satisfied a pending response, False otherwise
        """
        if channel_id in self.pending_responses:
            future = self.pending_responses[channel_id]
            if not future.done():
                future.set_result(message)
                del self.pending_responses[channel_id]
                return True
        return False

@dataclass
class Config:
    """Configuration for codeflow session."""
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
        user: Optional[User] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize session with its configuration.
        
        Args:
            user: The user interacting with the session (optional, defaults to CLIUser)
            config: Configuration options (optional)
        """
        self.user = user if user is not None else CLIUser()
        self.config = config or Config()
        self.logger = logging.getLogger("codeflow.session")
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
            default_config = Path.home() / ".codeflow" / "config.yaml"
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
        from codeflow.templates import load_all_teammates
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
    
    def setup_team(self, team_names: List[str]) -> 'Team':
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