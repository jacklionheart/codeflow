"""
Bot implementation for Discord integration.

This module provides the core bot functionality for the loopflow-server,
enabling Discord interactions with LLM mates. Each bot represents a single 
LLM mate and handles conversation with users in Discord channels.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union

from loopflow.llm import LLM

logger = logging.getLogger(__name__)

class Bot:
    """
    Base class for bot implementations.
    
    This provides a common interface for different bot types (Discord, CLI, etc.)
    and handles interaction with a configured LLM mate.
    """
    
    def __init__(self, mate_name: str, llm: LLM):
        """
        Initialize a bot for a specific mate.
        
        Args:
            mate_name: Name of the mate this bot represents
            llm: The configured LLM for this mate
        """
        self.mate_name = mate_name
        self.llm = llm
        self.logger = logging.getLogger(f"loopflow.bot.{mate_name}")
        self.logger.info(f"Initialized bot for mate '{mate_name}'")

    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process an incoming message and generate a response.
        
        Args:
            message: The incoming message text
            context: Optional context information (e.g., user ID, channel)
            
        Returns:
            The bot's response text
        """
        self.logger.debug(f"Processing message: {message[:50]}...")
        
        try:
            response = await self.llm.chat(message)
            self.logger.debug(f"Generated response: {response[:50]}...")
            return response
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            self.logger.error(error_msg)
            return f"I'm sorry, I encountered an error: {str(e)}"

class DiscordBot(Bot):
    """
    Discord-specific bot implementation.
    
    Handles Discord-specific functionality like formatting, message history,
    and Discord API integration.
    """
    
    def __init__(self, mate_name: str, llm: LLM, bot_id: str):
        """
        Initialize a Discord bot for a specific mate.
        
        Args:
            mate_name: Name of the mate this bot represents
            llm: The configured LLM for this mate
            bot_id: Discord bot ID for this mate
        """
        super().__init__(mate_name, llm)
        self.bot_id = bot_id
        self.user_histories: Dict[str, List[Dict[str, str]]] = {}
        self.logger.info(f"Initialized Discord bot for mate '{mate_name}' with ID {bot_id}")
    
    def get_user_history(self, user_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a specific user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        if user_id not in self.user_histories:
            self.user_histories[user_id] = []
        return self.user_histories[user_id]
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a Discord message and generate a response.
        
        Overrides the base method to handle Discord-specific context and history.
        
        Args:
            message: The incoming message text
            context: Context with user_id, channel_id, etc.
            
        Returns:
            The bot's response text
        """
        if not context or 'user_id' not in context:
            self.logger.warning("Missing user_id in context, using default")
            user_id = 'default'
        else:
            user_id = context['user_id']
        
        # Get user's conversation history
        history = self.get_user_history(user_id)
        
        # Add user message to history
        history.append({
            'role': 'user',
            'content': message
        })
        
        # Generate response using the LLM (with history maintained inside the LLM)
        response = await super().process_message(message, context)
        
        # Add bot response to history
        history.append({
            'role': 'assistant',
            'content': response
        })
        
        # Trim history if it gets too long (basic management)
        if len(history) > 100:  # Arbitrary limit, adjust as needed
            history = history[-100:]
            self.user_histories[user_id] = history
        
        return response