# Loopflow Communication Update

## Goal
Loopflow is currently a command line tool that helps you use llms to edit files (write code). Part of the system involves configuring LLMs ith system prompts to serve certain roles. Let's add a loopflow server that allows to chat with these LLMs. The overall goal should that we want to able to somehow have a chat thread with an LLM "mate" where the system prompt is used, and every time e send a reply, the discord bot forwards the chat to an LLM.

We can assume we have a discord server with admin access. Ideally, we use standard environment variables to load API keys.

There may need to be some sort of init function that creates a discord bot for a given llm (for now, ID by name).

Other than that, the server should mostly register for notifications with discord for this bot. When it receives chat messages (directly?), it should foraward the chat thread to the LLM and then post back the LLM's reply as a response in chat.  It is interseting to think about how this might work in channel contexts or otherise, but right now the focus shuold be identifying the most natural workflow and supporting that.


## Output
loopflow/chat/server.py
loopflow/chat/bot.py
loopflow/io/discord.py
loopflow/io/session.py