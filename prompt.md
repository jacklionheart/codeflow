# Loopflow Discord Integration

## Goal
We are currently beta-testing the most recent change of adding OpenAI support.
Our goal is to use loopflow to build a discord-based communication channel in Loopflow.
Instead of interacting on the command line, LoopflowBot (or similar) should message you on discord to get clarification.

I like the idea of having persistent chats with merlin and maya on discord. 
The context here is a small engineering team that I would like to be using loopflow. In the medium term I could imagine running a service someehre in the cloud to allow chatting with Merlin and Maya via discord. In the more immediate term maybe it makes sense to start with just a daemon service i run locally for myself. we can change the cli to basically enqueue jobs for the dameon.

Security and access control should be clear and well built out, but also I can use whatever process is simplest. I dont need to be able toreplicate my setup for others other than within my on company; I can find a place to store a secret. We can avoid things like roles if possible. We should be a simple plain text interface to start.

## Output
loopflow/daemon.py
loopflow/session.py
loopflow/workflow.py
loopflow/discord.py

## Context
loopflow/

## Team
maya
merlin
