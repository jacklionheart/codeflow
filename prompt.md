We are redesigning loopflow's core data structures as we continue to prototype it. 

We just introduce a Conversation abstraction, which encapsulates our 4 current "jobs" of clarifying, drafting, reviewing, and synthesizing.

Id like to change in a few ways. 

First, some renaming.

Conversation->Job
ClarificationConversation->Clarify (etc.)

Second, let's take this further and add the idea of a workflow that coordinates the sequence of jobs.

For right now the workflow is where the clarify-->draft-->review-->synthesize pipeline is defined..

Finally, let's add a session that instantiates the workflow and handles reporting usage, exception handling, and other operational concerns.

First start with a technical design:
- Diagram the new data structure hierarchy
- Review existing code to ensure that these new data structures will simplify and clarify the codebase
- Define the exact schemas and APIs for the new core data structures, and any key changes to existing ones
- Offer guidance on how to impelement in a way that optimizes for simplicity, clarity, and performance.