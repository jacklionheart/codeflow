# Loopflow Communication Update

## Goal
Loopflow is currently a command line tool that helps you use llms to edit files (write code). Part of the system involves configuring LLMs ith system prompts to serve certain roles. Let's add a loopflow server that allows to chat with these LLMs. The overall goal should that we want to able to somehow have a chat thread with an LLM "mate" where the system prompt is used, and every time e send a reply, the discord bot forwards the chat to an LLM.

We can assume we have a discord server with admin access. Ideally, we use standard environment variables to load API keys.

There may need to be some sort of init function that creates a discord bot for a given llm (for now, ID by name).

Other than that, the server should mostly register for notifications with discord for this bot. When it receives chat messages (directly?), it should foraward the chat thread to the LLM and then post back the LLM's reply as a response in chat.  It is interseting to think about how this might work in channel contexts or otherise, but right now the focus shuold be identifying the most natural workflow and supporting that.

-- Questions

--- maya's questions
To ensure alignment and clarity on the server-focused enhancements for Loopflow, let's delve into a few critical questions:

1. **Discord Bot Initialization and Identification:**
   - What are the specific roles or functions that each LLM bot should play in the Discord server? How should these be specified in the system prompt?
   - How do you envision mapping an LLM to a bot by name? Will there be a predefined list of LLMs, or do we need to consider dynamic mapping?
   - What are the necessary environment variables and configuration details needed to initiate a Discord bot and link it to an LLM effectively?


Each LLM is the same other than the (1) the system prompt (2) the chat thread history
We can use a database to save some basic discord bot IDs if necessary.
I dont know what discord APIs are required, that is on you for now.

2. **Interaction and Notification Workflow:**
   - Should the bot only respond to direct messages, or will it also handle messages in public or specific channels? How should it distinguish these cases?
   - How should responses be tailored based on the type of interaction (direct message vs. channel context)? Are there specific priorities for handling high-traffic channels?
   - What are the natural points of interaction between Discord's notification system and the LLM server? How should these be logged or tracked for user experience and error handling?

Right now let's just pick a single use pattern adn test that. We can pick whatever it is easiest. We dont need to worry about people abusing the system or hitting context limits yet.

3. **Conversation Thread Management:**
   - How do we maintain the context of a conversation between a user and an LLM mate across multiple messages? What data structures or techniques should be employed to manage conversation threads effectively?
   - Are there any security considerations in storing and processing these conversation threads, especially in relation to user data and privacy?

We shouldnt need to preserve any message state. We will just query the context/history from discord and present that to the LLM when asking them for a message.

4. **Bot Communication and API Design:**
   - What should the API between the Discord bot and the LLM look like in terms of endpoints, methods, and data formats? How do we ensure it is minimal yet complete?
   - How should errors be handled when communicating with LLMs (e.g., network failures, invalid inputs) to ensure a smooth user experience?

The discord server will:
- create bot accounts that it maps to specific names (once per mate, special command)
- whenever booted up, look for the discord bot ids for all the mates it knows about and the registers to listen for new messages to these bots. it then sends replies whenever a new message comes in after first gen'ing the reply on the LLM.


5. **Performance and Scalability:**
   - How do we ensure that the communication between the Discord bot, the chat server, and each LLM is performant, especially under high usage?
   - What potential performance bottlenecks might arise, and how can we design the system to minimize these from the outset?

While performance and scalability are longterm important, this is really a small-scale UX prototype.

--- merlin's questions
Let me explore some key questions that will help clarify the architecture and requirements for this Discord-based LLM chat system:

1. LLM Identity & State Management
- How should we maintain the chat history/context between a user and a specific LLM persona?
- Should each user get their own instance of an LLM persona, or should personas be shared across users?
- Do we need to persist chat histories between sessions?

Discord should persist the chat state.
Each user gets its own instance in that the contexts/histories are not shared. However the system prompts are shared across users of the LLM mate/

2. Interaction Patterns & Scope
- Should LLM personas be able to interact with each other in channels, or only directly with users?
- Do we want to support group chats where multiple users interact with the same LLM instance?
- Should LLM personas be able to access/modify files like in the CLI tool, or is this purely conversational?

No, LLMs will not have any access to user-visibile state outside of discord.

3. Configuration & Security
- How should we handle rate limiting and usage tracking across different users/channels?
- What configuration should be required vs optional when initializing a new LLM bot?
- How do we handle authentication and permissions for who can interact with which bots?

This is just going to run perosnallyu for me and my team. Whatever is simple.

The most important experiment here is the interaction pattern. Once we have proven that the basic flow
and set up works, we ill want to see wehther group threads or channels are a more useful context,
and more generally think about how to scale to larger contexts or "different threads"

## Output
loopflow/chat/server.py
loopflow/chat/bot.py
loopflow/io/discord.py
loopflow/io/session.py

## Team
merlin
maya
