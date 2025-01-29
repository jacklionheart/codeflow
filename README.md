# loopflow

A toolkit for collaborative code generation and exploration, combining structured LLM workflows with intelligent context management.

## Key Features

### `loopflow`: Structured Code Generation

loopflow breaks down the creation of files into a series of automated LLM interactions. 

loopflow:
- structures requests into specific files to seamlessly integrate with your codebase
- breaks prompts into an automated pipeline of sub-prompts
- working with teams of specialized LLMs for configurable focus

The current pipeline is this:
- Clarify: each mate asks questions to clarify the requirements; these are grouped and sent as a single request to the user to answer
- Generate: each mate generates a draft of the file
- Review: each mate reviews each other's draft and provides feedback
- Synthesize: one mate synthesizes the feedback and provides a final draft

### Team Members

loopflow comes with two initial team members:
- maya: infrastructure engineer at a large tech company, focused on simplicity and robustness
- merlin: ML researcher specializing in novel architectures and mathematical abstractions

Adding more team members is TBD but coming.

### `code-context`: Smart Context Management

code-context is a spiritual successor to [files-to-prompt](https://github.com/simonw/files-to-prompt), 
a tool for specifying and formatting a subset of a codebase to submit as context to an LLM.

code-context builds on files-to-prompt with additional features:
- Automatic detection and prioritization of parent READMEs
- Smart path resolution based on common codebase structures

## Installation

This is still very early in development. Contact jack@loopflow.studio with any questions.

Requires Python 3.11+
```bash
pip install -e .
```

## Usage

### Structured Code Generation

Create a prompt file defining your requirements:

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

Run the workflow:
```bash
loopflow path/to/prompt.md
```

### Context Management

Copy specific paths to clipboard (OS X):
```bash
code-context -p myproject/src,myproject/tests
```

Filter to specific file types:
```bash
code-context -e .py -e .js myproject
```

Generate raw output:
```bash
code-context -r myproject
```

#### Path Resolution

The code-context tool uses smart defaults for finding files:

- Paths are relative to $CODE_CONTEXT_ROOT (default: ~/src)
- Direct paths are tried first: "myproj/env" -> "$CODE_CONTEXT_ROOT/myproj/env"
- Auto-prefixed paths are used as fallback: "myproj/env" -> "$CODE_CONTEXT_ROOT/myproj/myproj/env"
- Test directories are always at "myproj/tests"

## Configuration

Create ~/.loopflow/config.yaml:

```yaml
accounts:
  anthropic:
    api_key: "your-key-here"
```

## License

MIT