import pytest
from pathlib import Path
from textwrap import dedent
from loopflow.prompt import Prompt, PromptError

@pytest.fixture
def make_prompt_file():
    """
    Creates a fixture that helps generate prompt files with given content.
    The fixture takes care of creating and cleaning up temporary files.
    """
    def _make_file(tmp_path: Path, content: str) -> Path:
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text(dedent(content))
        return prompt_file
    return _make_file

def test_complete_prompt_parsing(tmp_path, make_prompt_file):
    """
    Tests parsing of a well-formed prompt with all sections populated.
    This represents the ideal case where users follow the format exactly.
    """
    content = """
        # ML Model Implementation

        ## Goal
        Build a neural network classifier for image recognition.

        ## Output
        model/classifier.py
        model/training.py

        ## Context
        data/images
        model/base.py

        ## Reviewers
        - ml_researcher
        - data_scientist
        """
    
    prompt_file = make_prompt_file(tmp_path, content)
    prompt = Prompt.from_file(prompt_file)
    
    # Verify each section is parsed correctly
    assert prompt.goal == "Build a neural network classifier for image recognition."
    assert prompt.output_files == ["model/classifier.py", "model/training.py"]
    assert prompt.context_files == ["data/images", "model/base.py"]
    assert set(prompt.reviewers) == {"ml_researcher", "data_scientist"}

def test_minimal_prompt_parsing(tmp_path, make_prompt_file):
    """
    Tests parsing of a prompt with only the required sections.
    This represents the minimal valid case that should be accepted.
    """
    content = """
        # Simple Task

        ## Goal
        Generate a utility function.

        ## Output
        utils.py

        ## Reviewers
        - software_engineer
        """
    
    prompt_file = make_prompt_file(tmp_path, content)
    prompt = Prompt.from_file(prompt_file)
    
    assert prompt.goal == "Generate a utility function."
    assert prompt.output_files == ["utils.py"]
    assert prompt.context_files is None  # Optional section omitted
    assert prompt.reviewers == ["software_engineer"]

def test_whitespace_handling(tmp_path, make_prompt_file):
    """
    Tests that the parser handles various whitespace patterns correctly.
    Users might include extra spaces, blank lines, or inconsistent indentation.
    """
    content = """
        # Whitespace Test

        ## Goal
           Indented goal with trailing space  

        ## Output
          file1.py  
         file2.py

        ## Reviewers
          - reviewer1  
          - reviewer2  
        """
    
    prompt_file = make_prompt_file(tmp_path, content)
    prompt = Prompt.from_file(prompt_file)
    
    assert prompt.goal == "Indented goal with trailing space"
    assert prompt.output_files == ["file1.py", "file2.py"]
    assert prompt.reviewers == ["reviewer1", "reviewer2"]

def test_prompt_validation_errors(tmp_path, make_prompt_file):
    """
    Tests various validation error conditions to ensure proper error reporting.
    Each case tests a specific way a prompt might be invalid.
    """
    error_cases = {
        "missing_goal": ("""
            ## Output
            test.py
            ## Reviewers
            - reviewer1
            """, 
            "Goal section is required"
        ),
        "missing_output": ("""
            ## Goal
            Test goal
            ## Reviewers
            - reviewer1
            """,
            "At least one output file is required"  # Changed to match implementation
        ),
        "empty_output": ("""
            ## Goal
            Test goal
            ## Output

            ## Reviewers
            - reviewer1
            """,
            "At least one output file is required"
        ),
        "missing_reviewers": ("""
            ## Goal
            Test goal
            ## Output
            test.py
            """,
            "At least one reviewer is required"  # Changed from "Reviewers section is required"
        ),
        "empty_reviewers": ("""
            ## Goal
            Test goal
            ## Output
            test.py
            ## Reviewers
            """,
            "At least one reviewer is required"
        )
    }
    
    for case_name, (content, expected_error) in error_cases.items():
        prompt_file = make_prompt_file(tmp_path, content)
        
        with pytest.raises(PromptError, match=expected_error):
            prompt = Prompt.from_file(prompt_file)
            prompt.validate()

def test_context_file_parsing(tmp_path, make_prompt_file):
    """
    Tests different ways context files can be specified.
    Users might provide single files, multiple files, or various separators.
    """
    variants = [
        ("src/lib", ["src/lib"]),
        ("src/lib,tests", ["src/lib", "tests"]),
        ("model.py, utils.py, data/", ["model.py", "utils.py", "data/"]),
        ("", None),  # Empty context is allowed
    ]
    
    for input_context, expected in variants:
        content = f"""
            ## Goal
            Test goal
            ## Output
            test.py
            ## Context
            {input_context}
            ## Reviewers
            - reviewer1
            """
        
        prompt_file = make_prompt_file(tmp_path, content)
        prompt = Prompt.from_file(prompt_file)
        assert prompt.context_files == expected