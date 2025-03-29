# CLAUDE.md - Loopflow Project Guide

## Commands
- Install: `pip install -e .`
- Run: `loopflow path/to/prompt.md`
- Tests: `python -m pytest`
- Run single test: `python -m pytest tests/path/to/test_file.py::test_function -v`
- Run tests with specific mark: `python -m pytest -m markname`
- Run last failed tests: `python -m pytest --lf`

## Code Style
- Python 3.11+ required
- Imports: standard lib → third-party → project imports, alphabetically within groups
- Type hints: required for all functions, parameters, returns, class attributes
- Naming: PascalCase (classes), snake_case (functions/variables), SCREAMING_SNAKE_CASE (constants)
- Private methods/functions prefixed with underscore (_method_name)
- Error handling: custom exception classes, contextual error messages, proper logging
- Testing: pytest fixtures, parametrized tests, descriptive test names (test_should_...)

## Project Structure
- CLI tools in loopflow/cli/
- LLM providers in loopflow/llm/
- Templates in loopflow/templates/
- Runtime components in loopflow/run/
- Tests mirror the package structure (tests/llm/, etc.)