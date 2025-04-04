# loopflow

**loopflow** is a workflow system for a graphs of structured llm requests for codegen.

## License
MIT

## How it works

loopflow has two primary interfaces:
* the *loopflow.md*, which defines the prompt(s) sent to llms by defining *goals*, *output_files*, and other metadata
* the *loopflow CLI*, which executes commands.

loopflow is built around "mates": LLMs with pre-defined system prompts to act in specific roles (currently: infrastructure engineer, research scientist). Commands can be run either against a specific mate or against a whole "team" of "mates", in which multiple LLMs handle requests and those responses are concatenated.

### Commands

The core loopflow commands:
- **Clarify**: Ask LLMs to generate questions to clarify the design.
- **Draft**: Ask LLMs to generate the *output_files*.
  -  *Single Mate Mode* (faster): One mate directly drafts each file
  - *Team Mode* (longer): The mates both draft and then review eac others' work, and then one synthesizes the final result
- **Review**: Asks LLMs to review the current drafts of the output files.

To invoke:
```bash
# Initialize a new loopflow project
loopflow init [project_dir]
# Generate questions to clarify requirements
loopflow clarify [project_dir]
# Draft files (uses full team by default with a draft->review->synthesize subpipeline)
loopflow draft [project_dir] [--mate <mate_name>]
# Review existing files and append feedback
loopflow review [project_dir]
# Reset git history to before loopflow checkpoints
loopflow rebase [project_dir]
```

### Team Members

loopflow is built around the general idea of "mates". Many different mates could be defined for different contexts.

The following two are the defaults currently available:
- maya: infrastructure engineer at a large tech company, focused on simplicity and robustness
- merlin: ML researcher specializing in novel architectures and mathematical abstractions

You can add mates in `templates/mates`; simply creating the file is sufficient for it be available.

### `code-context`: Smart Context Management

Key to loopflow is submitting the right context, i.e. subset of the codebase as a reference. This is
a part of how loopflow works, but installing loopflow also installs a `code-context` binary that is
used to copy codebase subsets to the clipboard or other output streams.

code-context is a spiritual descendent of [files-to-prompt](https://github.com/simonw/files-to-prompt), 
a tool for specifying and formatting a subset of a codebase to submit as context to an LLM.

code-context builds on files-to-prompt with additional features:
- Automatic detection and prioritization of parent READMEs
- Smart path resolution based on common codebase structures

Perhaps the biggest area of current development is exploring how to best filter and compress large codebases. 
Right now the burden is on the user to identify the right subset via the code-context tool.
I believe that empowering the user to quickly express intent is essential, but it is not enough.
Work in ideas like summarization or indexing or RAG are on-going.

```bash
# Copy specific paths to clipboard (OS X):
code-context -p myproject/src,myproject/tests

# Filter to specific file types
code-context -e .py -e .js myproject

# Generate raw output instead of XML-wrapped:
code-context -r myproject
```

## Installation

Requires Python 3.11+
```bash
pip install -e .
```

Contact jack@loopflow.studio with any questions. Kinks likely not ironed out.

You must set `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` in your environment to use those providers.

## Prompt Files

You can create a prompt file template with `loopflow init`. 

They should look like this:
```markdown
# Loopflow LLM Implementation

## Goal
Implement the LLM API for loopflow, a tool for generating code with teams of LLMs.

## Output
loopflow/llm/llm.py
loopflow/llm/anthropic.py
loopflow/tests/test_llm.py

## Context
loopflow/

## Team
maya
merlin
```
