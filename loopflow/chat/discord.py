"""
Discord integration for loopflow.

This module provides the server-side implementation for loopflow's Discord integration,
enabling chat-based interactions with LLM mates through Discord.
"""

import asyncio
import logging
import os
import yaml
from flask import Flask, request, jsonify
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from loopflow.bot import DiscordBot
from loopflow.llm import LLMProvider, LLM
from loopflow.templates import load_all_teammates

logger = logging.getLogger(__name__)

class DiscordConfig:
    """
    Configuration for Discord integration.
    
    Handles loading and validating Discord configuration from a config file.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize Discord configuration.
        
        Args:
            config_path: Path to config file (defaults to ~/.loopflow/discord_config.yaml)
        """
        self.config_path = config_path or Path.home() / ".loopflow" / "discord_config.yaml"
        self.bot_tokens: Dict[str, str] = {}
        self.server_url: str = ""
        self.guild_id: str = ""
        self.application_id: str = ""
        self.enabled_mates: List[str] = []
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            logger.warning(f"Discord config file not found at {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.server_url = config.get('server_url', '')
            self.guild_id = config.get('guild_id', '')
            self.application_id = config.get('application_id', '')
            self.enabled_mates = config.get('enabled_mates', [])
            self.bot_tokens = config.get('bot_tokens', {})
            
            logger.info(f"Loaded Discord config with {len(self.bot_tokens)} bot tokens")
            logger.info(f"Enabled mates: {self.enabled_mates}")
        except Exception as e:
            logger.error(f"Error loading Discord config: {e}")

class LoopflowServer:
    """
    Server implementation for loopflow's Discord integration.
    
    This class manages the Flask server and Discord bot instances,
    handling message routing and mate management.
    """
    
    def __init__(
        self, 
        providers: Dict[str, LLMProvider],
        config_path: Optional[Path] = None
    ):
        """
        Initialize the loopflow Discord server.
        
        Args:
            providers: Dictionary of LLM providers
            config_path: Optional path to Discord config file
        """
        self.providers = providers
        self.config = DiscordConfig(config_path)
        self.bots: Dict[str, DiscordBot] = {}
        self.flask_app = Flask("loopflow-server")
        self.logger = logging.getLogger("loopflow.discord.server")
        
        self._init_routes()
    
    def _init_routes(self) -> None:
        """Initialize Flask routes."""
        @self.flask_app.route('/webhook', methods=['POST'])
        def webhook():
            """Handle incoming Discord webhook events."""
            try:
                data = request.json
                
                # Basic validation
                if not data or 'mate' not in data or 'message' not in data:
                    return jsonify({'error': 'Invalid request format'}), 400
                
                mate_name = data['mate']
                message = data['message']
                user_id = data.get('user_id', 'unknown')
                channel_id = data.get('channel_id', 'unknown')
                
                # Process asynchronously
                loop = asyncio.new_event_loop()
                response = loop.run_until_complete(
                    self._process_message(mate_name, message, user_id, channel_id)
                )
                loop.close()
                
                return jsonify({'response': response})
            except Exception as e:
                self.logger.error(f"Error processing webhook: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.flask_app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'bots': list(self.bots.keys())
            })
    
    async def _process_message(
        self, mate_name: str, message: str, user_id: str, channel_id: str
    ) -> str:
        """
        Process a message for a specific mate.
        
        Args:
            mate_name: Name of the mate to process the message
            message: The message text
            user_id: Discord user ID
            channel_id: Discord channel ID
            
        Returns:
            The bot's response text
        """
        if mate_name not in self.bots:
            error_msg = f"Unknown mate: {mate_name}"
            self.logger.error(error_msg)
            return f"Error: {error_msg}"
        
        context = {
            'user_id': user_id,
            'channel_id': channel_id
        }
        
        return await self.bots[mate_name].process_message(message, context)
    
    def setup_bots(self) -> None:
        """Set up Discord bots for all enabled mates."""
        self.logger.info("Setting up Discord bots")
        
        # Load all teammate configurations
        teammates = load_all_teammates()
        
        for mate_name in self.config.enabled_mates:
            if mate_name not in teammates:
                self.logger.warning(f"Skipping unknown mate: {mate_name}")
                continue
            
            if mate_name not in self.config.bot_tokens:
                self.logger.warning(f"Skipping mate without bot token: {mate_name}")
                continue
            
            mate_config = teammates[mate_name]
            provider_name = mate_config.provider
            
            if provider_name not in self.providers:
                self.logger.warning(f"Skipping mate with unknown provider: {provider_name}")
                continue
            
            # Create LLM for the mate
            provider = self.providers[provider_name]
            llm = provider.createLLM(
                name=mate_name, 
                system_prompt=mate_config.system_prompt
            )
            
            # Create Discord bot
            bot_id = mate_name  # For now, use mate name as bot ID
            bot = DiscordBot(mate_name, llm, bot_id)
            self.bots[mate_name] = bot
            
            self.logger.info(f"Set up Discord bot for mate: {mate_name}")
        
        self.logger.info(f"Set up {len(self.bots)} Discord bots")
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False) -> None:
        """
        Run the Flask server.
        
        Args:
            host: Host to listen on
            port: Port to listen on
            debug: Whether to run in debug mode
        """
        self.setup_bots()
        self.logger.info(f"Starting loopflow-server on {host}:{port}")
        self.flask_app.run(host=host, port=port, debug=debug)

def setup_discord_server(providers: Dict[str, LLMProvider]) -> LoopflowServer:
    """
    Set up the loopflow Discord server.
    
    Args:
        providers: Dictionary of LLM providers
        
    Returns:
        Configured LoopflowServer instance
    """
    server = LoopflowServer(providers)
    return server