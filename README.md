# loopflow

A tool for generating code through structured collaboration between humans and LLMs.

## Core Concept

Loopflow helps humans and LLMs work together through a cycle of clarifying questions, parallel generation, and review. Instead of trying to generate perfect code in one shot, it breaks the process into steps where understanding can be refined.

## How It Works

A prompt file specifies the requirements, output files, context, and reviewers:

```markdown
# Authentication Implementation

## Output Files
- manabot/ppo/model.pyr

## Context
- manabot/

## Reviewers
- data_scientist
- ml_researcher

## Requirements
Implement a secure authentication system supporting username/password 
and OAuth2 providers. The system should be extensible for new 
authentication methods...
```

When run, loopflow:
1. Has LLMs ask clarifying questions about requirements
2. Generates independent drafts after receiving answers
3. Reviews drafts from different perspectives
4. Creates a final version incorporating review feedback

## Usage

```bash
loopflow path/to/prompt.md
```

Prompts typically live in your codebase under a `prompts` directory and are versioned with your code.

## Status

Early development focused on:
- Basic generation and review workflow
- Discord notifications for feedback
- Integration with code-context
- Cost tracking
