```python
import os
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from loopflow.io.session import SessionManager
from loopflow.io.discord import DiscordIO
from loopflow.io.config import Config

logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    calls: int = 0
    reset_time: datetime = field(default_factory=datetime.now)
    max_calls: int = 50
    window: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    
    def can_make_call(self) -> bool:
        now = datetime.now()
        if now > self.reset_time + self.window:
            self.calls = 0
            self.reset_time = now
        return self.calls < self.max_calls
    
    def record_call(self):
        self.calls += 1

class LoopflowChatServer:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.session_manager = SessionManager(
            storage_dir=self.config.session_storage_path
        )
        self.openai_client = openai.OpenAI(
            api_key=self.config.openai_api_key
        )
        self.rate_limits: Dict[str, RateLimit] = {}
        self.bots: Dict[str, commands.Bot] = {}
        
        # Start auto-save task
        asyncio.create_task(self.session_manager.auto_save())
    
    def get_rate_limit(self, key: str) -> RateLimit:
        if key not in self.rate_limits:
            self.rate_limits[key] = RateLimit()
        return self.rate_limits[key]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_llm_response(
        self,
        messages: List[dict],
        channel_id: int
    ) -> str:
        rate_limit = self.get_rate_limit(str(channel_id))
        if not rate_limit.can_make_call():
            raise Exception("Rate limit exceeded")
            
        try:
            response = await asyncio.to_thread(
                lambda: self.openai_client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages
                )
            )
            rate_limit.record_call()
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            raise
    
    async def create_bot(self, name: str, system_prompt: str) -> None:
        if name in self.bots:
            raise ValueError(f"Bot {name} already exists")
            
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix=self.config.command_prefix, intents=intents)
        
        # Create or load session
        session = await asyncio.to_thread(
            lambda: self.session_manager.create_session(
                name,
                system_prompt,
                bot_name=name
            )
        )
        
        @bot.event
        async def on_ready():
            logger.info(f"Bot {name} is ready!")
        
        @bot.event
        async def on_message(message):
            if message.author == bot.user:
                return
                
            # Only respond to DMs or when mentioned
            if not (
                isinstance(message.channel, discord.DMChannel) or 
                bot.user in message.mentions
            ):
                await bot.process_commands(message)
                return
            
            async with message.channel.typing():
                try:
                    # Get conversation context
                    context = session.get_context(
                        max_messages=self.config.max_history
                    )
                    
                    # Add user message
                    session.add_message(
                        "user",
                        message.content,
                        author_id=message.author.id
                    )
                    
                    # Get LLM response
                    reply = await self.get_llm_response(
                        context,
                        message.channel.id
                    )
                    
                    # Add response to history
                    session.add_message(
                        "assistant",
                        reply
                    )
                    
                    # Send response in chunks if needed
                    if len(reply) > 2000:
                        chunks = [
                            reply[i:i+2000] 
                            for i in range(0, len(reply), 2000)
                        ]
                        for chunk in chunks:
                            await message.reply(chunk)
                    else:
                        await message.reply(reply)
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await message.reply(
                        f"Sorry, I encountered an error: {str(e)}"
                    )
        
        @bot.command()
        async def reset(ctx):
            """Reset conversation history"""
            session.clear()
            await ctx.send("Conversation history has been reset.")
        
        @bot.command()
        async def prompt(ctx):
            """Show current system prompt"""
            await ctx.send(f"Current system prompt: {session.system_prompt}")
        
        self.bots[name] = bot
        
        # Start bot
        token = self.config.get_bot_token(name)
        if not token:
            raise ValueError(f"No Discord token found for bot {name}")
            
        await bot.start(token)
    
    async def shutdown(self):
        """Shutdown all bots and save sessions"""
        for bot in self.bots.values():
            await bot.close()
        await self.session_manager.save_all()

async def main():
    logging.basicConfig(level=logging.INFO)
    server = LoopflowChatServer()
    
    try:
        await server.create_bot(
            "researcher",
            "You are a helpful research assistant..."
        )
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await server.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```