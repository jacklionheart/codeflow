```python
import os
import asyncio
import logging
from typing import Optional, Dict, List, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

import discord
from discord import Message, TextChannel, DMChannel, Embed
from discord.ext import tasks

logger = logging.getLogger(__name__)

@dataclass
class DiscordMetrics:
    messages_sent: int = 0
    messages_edited: int = 0
    errors: int = 0
    last_error: Optional[str] = None
    avg_response_time: float = 0.0
    last_active: datetime = field(default_factory=datetime.now)

@dataclass
class DiscordConfig:
    """Configuration for Discord client"""
    token: str
    default_channel_id: Optional[int] = None
    guild_id: Optional[int] = None
    command_prefix: str = "!"
    reconnect_attempts: int = 3
    heartbeat_interval: int = 30
    max_message_length: int = 2000
    rate_limit_messages: int = 5
    rate_limit_window: int = 5
    allowed_mentions: List[str] = field(default_factory=lambda: ["users"])

class DiscordIO:
    """Discord I/O handler with support for message management and metrics"""
    
    def __init__(self, config: DiscordConfig):
        self.config = config
        self.client = discord.Client(
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(
                users=True if "users" in config.allowed_mentions else False,
                roles=True if "roles" in config.allowed_mentions else False,
                everyone=True if "everyone" in config.allowed_mentions else False
            )
        )
        self._channel: Optional[TextChannel] = None
        self._ready = asyncio.Event()
        self._handlers: Dict[str, List[Callable[[Message], Awaitable[None]]]] = {
            "message": [],
            "reaction": [],
            "error": []
        }
        self.metrics = DiscordMetrics()
        self._setup_handlers()
        self._start_tasks()

    def _setup_handlers(self):
        @self.client.event
        async def on_ready():
            logger.info(f"Discord client logged in as {self.client.user}")
            if self.config.default_channel_id:
                channel = self.client.get_channel(self.config.default_channel_id)
                if isinstance(channel, (TextChannel, DMChannel)):
                    self._channel = channel
            self._ready.set()

        @self.client.event
        async def on_message(message):
            if message.author == self.client.user:
                return
            
            try:
                for handler in self._handlers["message"]:
                    await handler(message)
            except Exception as e:
                self.metrics.errors += 1
                self.metrics.last_error = str(e)
                logger.error(f"Error in message handler: {e}")
                for handler in self._handlers["error"]:
                    await handler(e)

        @self.client.event
        async def on_error(event, *args, **kwargs):
            self.metrics.errors += 1
            error = args[0] if args else "Unknown error"
            self.metrics.last_error = str(error)
            logger.error(f"Discord error in {event}: {error}")
            for handler in self._handlers["error"]:
                await handler(error)

    def _start_tasks(self):
        @tasks.loop(seconds=self.config.heartbeat_interval)
        async def heartbeat():
            if not self._ready.is_set():
                return
            
            now = datetime.now()
            if now - self.metrics.last_active > timedelta(minutes=5):
                logger.info("Client inactive, checking connection...")
                if not self.client.is_ready():
                    logger.warning("Client disconnected, attempting reconnect")
                    await self.reconnect()

        heartbeat.start()

    async def start(self):
        """Start the Discord client with retry logic"""
        @retry(
            stop=stop_after_attempt(self.config.reconnect_attempts),
            wait=wait_exponential(multiplier=1, min=4, max=10)
        )
        async def _start():
            try:
                await self.client.start(self.config.token)
            except Exception as e:
                logger.error(f"Failed to start Discord client: {e}")
                raise

        await _start()

    async def stop(self):
        """Stop the Discord client"""
        await self.client.close()

    async def reconnect(self):
        """Reconnect the Discord client"""
        try:
            await self.client.close()
            self._ready.clear()
            await self.start()
        except Exception as e:
            logger.error(f"Failed to reconnect: {e}")
            raise

    async def wait_ready(self):
        """Wait until Discord client is ready"""
        await self._ready.wait()

    async def get_channel(self, channel_id: Optional[int] = None) -> Optional[TextChannel]:
        """Get channel by ID or default channel"""
        await self.wait_ready()
        
        channel = None
        if channel_id:
            channel = self.client.get_channel(channel_id)
        elif self._channel:
            channel = self._channel
            
        if not channel:
            raise ValueError("No valid channel specified or configured")
            
        return channel

    async def send_message(
        self,
        content: str,
        channel_id: Optional[int] = None,
        embed: Optional[Embed] = None,
        reference: Optional[Message] = None
    ) -> List[Message]:
        """Send a message, splitting if needed"""
        channel = await self.get_channel(channel_id)
        messages = []
        
        try:
            if len(content) <= self.config.max_message_length:
                msg = await channel.send(
                    content=content,
                    embed=embed,
                    reference=reference
                )
                messages.append(msg)
            else:
                chunks = [
                    content[i:i+self.config.max_message_length]
                    for i in range(0, len(content), self.config.max_message_length)
                ]
                for i, chunk in enumerate(chunks):
                    msg = await channel.send(
                        content=chunk,
                        embed=embed if i == 0 else None,
                        reference=reference if i == 0 else None
                    )
                    messages.append(msg)
                    
            self.metrics.messages_sent += 1
            self.metrics.last_active = datetime.now()
            
        except Exception as e:
            self.metrics.errors += 1
            self.metrics.last_error = str(e)
            logger.error(f"Error sending message: {e}")
            raise
            
        return messages

    async def edit_message(
        self,
        message_id: int,
        content: str,
        channel_id: Optional[int] = None
    ) -> Message:
        """Edit an existing message"""
        channel = await self.get_channel(channel_id)
        
        try:
            message = await channel.fetch_message(message_id)
            edited = await message.edit(content=content)
            self.metrics.messages_edited += 1
            return edited
        except Exception as e:
            self.metrics.errors += 1
            self.metrics.last_error = str(e)
            logger.error(f"Error editing message: {e}")
            raise

    async def delete_message(
        self,
        message_id: int,
        channel_id: Optional[int] = None
    ):
        """Delete a message"""
        channel = await self.get_channel(channel_id)
        
        try:
            message = await channel.fetch_message(message_id)
            await message.delete()
        except Exception as e:
            self.metrics.errors += 1
            self.metrics.last_error = str(e)
            logger.error(f"Error deleting message: {e}")
            raise

    def add_handler(
        self,
        event: str,
        handler: Callable[[Any], Awaitable[None]]
    ):
        """Add an event handler"""
        if event not in self._handlers:
            raise ValueError(f"Unknown event type: {event}")
        self._handlers[event].append(handler)

    @staticmethod
    def from_env(
        token_var: str = "DISCORD_TOKEN",
        channel_var: str = "DISCORD_CHANNEL_ID",
        guild_var: str = "DISCORD_GUILD_ID",
        **kwargs
    ) -> 'DiscordIO':
        """Create DiscordIO instance from environment variables"""
        token = os.getenv(token_var)
        if not token:
            raise ValueError(f"Missing {token_var} environment variable")
            
        channel_id = os.getenv(channel_var)
        guild_id = os.getenv(guild_var)
        
        config = DiscordConfig(
            token=token,
            default_channel_id=int(channel_id) if channel_id else None,
            guild_id=int(guild_id) if guild_id else None,
            **kwargs
        )
        
        return DiscordIO(config)

async def create_discord_io(
    token: Optional[str] = None,
    channel_id: Optional[int] = None,
    guild_id: Optional[int] = None,
    **kwargs
) -> DiscordIO:
    """Create and initialize a DiscordIO instance"""
    if not token:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("No Discord token provided")
            
    config = DiscordConfig(
        token=token,
        default_channel_id=channel_id,
        guild_id=guild_id,
        **kwargs
    )
    
    discord_io = DiscordIO(config)
    asyncio.create_task(discord_io.start())
    await discord_io.wait_ready()
    return discord_io
```