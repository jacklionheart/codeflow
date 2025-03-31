# Loopflow Communication Update

## Goal
Let's change the main workflow of loopflow to two separate invocations. The first, "clarify", will output directly to the prompt file that was used to generate the request. 
We will ask the llm mates to each generate questions as before, and we will simply append what was being sent as a message to the cli to the prompt file.

The user can then update the prompt to include the questions.  THe user will then invoke a separate step ("team", will run the draft->review->synthesize flow as before. "mate" should be just a draft with a specific mate (with some default).
This separation in workflow should be thought through carefully and handled thoroughly, from the command-line to the inner job abstractions. 

We were previously planning to use Discord to handle the clarifiucation process. Instead, lets introduce a totally separate service, loopflow-server, which will be a server-side daemon that enables you to chat with a mate-configured llm on discord. This will live outside the editing workflow and the context provided to the LLM will be the same as the chat history in discord. 
We don't need to fully implement this yet, but we should adapt any communication or User concepts to set the ground work for this inthe future.

## Output
loopflow/bot.py
loopflow/session.py
loopflow/workflow.py
loopflow/discord.py
