```python
import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from tenacity import retry, stop_after_attempt, wait_exponential

from loopflow.io.session import Session, SessionManager
from loopflow.io.config import Config
from loopflow.chat.handlers import MessageHandler, CommandHandler

logger = logging.getLogger(__name__)

@dataclass
class BotMetrics:
    messages_processed: int = 0
    errors_encountered: int = 0
    last_error: Optional[str] = None
    last_active: datetime = field(default_factory=datetime.now)
    avg_response_time: float = 0.0

class LoopflowBot(commands.Bot):
    """A Discord bot powered by an LLM with persistent conversation history"""
    
    def __init__(
        self,
        name: str,
        config: Config,
        session_manager: SessionManager,
        message_handler: Optional[MessageHandler] = None,
        command_handler: Optional[CommandHandler] = None,
        **kwargs
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            **kwargs
        )
        
        self.name = name
        self.config = config
        self.session_manager = session_manager
        self.message_handler = message_handler or MessageHandler(config)
        self.command_handler = command_handler or CommandHandler()
        self.metrics = BotMetrics()
        
        # Register commands
        self.setup_commands()
        
    def setup_commands(self):
        """Register bot commands"""
        
        @self.command(name="reset")
        async def reset_history(ctx):
            """Reset conversation history for this channel"""
            session = await self.get_session(ctx.channel.id)
            session.clear()
            await ctx.send("Conversation history has been reset.")
            
        @self.command(name="stats")
        async def show_stats(ctx):
            """Show bot statistics"""
            embed = discord.Embed(title=f"{self.name} Statistics")
            embed.add_field(
                name="Messages Processed",
                value=self.metrics.messages_processed
            )
            embed.add_field(
                name="Average Response Time",
                value=f"{self.metrics.avg_response_time:.2f}s"
            )
            if self.metrics.last_error:
                embed.add_field(
                    name="Last Error",
                    value=self.metrics.last_error
                )
            await ctx.send(embed=embed)
            
        @self.command(name="prompt")
        async def show_prompt(ctx):
            """Show current system prompt"""
            session = await self.get_session(ctx.channel.id)
            await ctx.send(f"Current system prompt: {session.system_prompt}")
    
    async def get_session(self, channel_id: int) -> Session:
        """Get or create session for channel"""
        session_id = f"{self.name}_{channel_id}"
        session = self.session_manager.get_session(session_id)
        
        if not session:
            session = await asyncio.to_thread(
                lambda: self.session_manager.create_session(
                    session_id,
                    self.config.default_system_prompt,
                    channel_id=channel_id,
                    bot_name=self.name
                )
            )
        
        return session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def process_message(self, message: discord.Message) -> Optional[str]:
        """Process a message and return response if appropriate"""
        try:
            start_time = datetime.now()
            
            # Get session for this channel
            session = await self.get_session(message.channel.id)
            
            # Process message
            response = await self.message_handler.handle(
                message.content,
                session,
                user_id=message.author.id,
                channel_id=message.channel.id
            )
            
            # Update metrics
            self.metrics.messages_processed += 1
            elapsed = (datetime.now() - start_time).total_seconds()
            self.metrics.avg_response_time = (
                self.metrics.avg_response_time * 0.9 + elapsed * 0.1
            )
            self.metrics.last_active = datetime.now()
            
            return response
            
        except Exception as e:
            self.metrics.errors_encountered += 1
            self.metrics.last_error = str(e)
            logger.error(f"Error processing message: {e}")
            raise
    
    async def setup_hook(self):
        """Setup hook called before bot starts"""
        logger.info(f"Bot {self.name} is setting up...")
        
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"{self.name} is ready and online!")
        
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        if message.author == self.user:
            return
            
        # Only respond to DMs or when mentioned
        if not (
            isinstance(message.channel, discord.DMChannel) or 
            self.user in message.mentions
        ):
            await self.process_commands(message)
            return
            
        async with message.channel.typing():
            try:
                response = await self.process_message(message)
                if response:
                    # Split long messages
                    if len(response) > 2000:
                        chunks = [
                            response[i:i+2000] 
                            for i in range(0, len(response), 2000)
                        ]
                        for chunk in chunks:
                            await message.reply(chunk)
                    else:
                        await message.reply(response)
                        
            except Exception as e:
                await message.reply(
                    f"Sorry, I encountered an error: {str(e)}"
                )

async def create_bot(
    name: str,
    config: Optional[Config] = None,
    session_manager: Optional[SessionManager] = None,
    **kwargs
) -> LoopflowBot:
    """Create and initialize a new bot instance"""
    config = config or Config.from_env()
    session_manager = session_manager or SessionManager()
    
    bot = LoopflowBot(
        name=name,
        config=config,
        session_manager=session_manager,
        **kwargs
    )
    
    token = config.get_bot_token(name)
    if not token:
        raise ValueError(f"No Discord token found for bot {name}")
        
    async def start_bot():
        try:
            await bot.start(token)
        except Exception as e:
            logger.error(f"Error starting bot {name}: {e}")
            raise
            
    asyncio.create_task(start_bot())
    return bot
```