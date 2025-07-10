# codeflow

**codeflow** is a tool for copying a codebase (or parts of it) for use with LLM prompts.

## How it works

codeflow is a spiritual descendant of [files-to-prompt](https://github.com/simonw/files-to-prompt), 
a tool for specifying and formatting a subset of a codebase to submit as context to an LLM.

codeflow builds on files-to-prompt with additional features:
- Automatic detection and prioritization of parent READMEs
- Token profiling to understand context window usage
- Flame graph visualization of token distribution

## Usage

```bash
# Copy current directory to clipboard (macOS):
codeflow -p

# Copy specific paths (space-separated, relative to current directory):
codeflow src tests

# Filter to specific file types:
codeflow -e .py -e .js src

# Generate raw output instead of XML-wrapped:
codeflow -r src tests

# Profile token usage:
codeflow --profile src

# Generate interactive flame graph of token distribution:
codeflow --flamegraph src
```

## Installation

Requires Python 3.11+ and `uv`
```bash
uv tool install -e .
```

Contact jack@loopflow.studio with any questions. Kinks likely not ironed out.


## License
MIT
