import pytest
import asyncio
from pathlib import Path
from loopflow.compose.pipeline import (
    ClarifyPipeline, MatePipeline, ReviewPipeline, TeamPipeline
)
from loopflow.compose.prompt import Prompt
from loopflow.io.session import User
from loopflow.llm.mate import Team

# A minimal dummy session object for pipeline testing.
class DummySession:
    def __init__(self, user: User, temp_dir: Path, dummy_team: Team):
        self.user = user
        self._temp_dir = temp_dir
        self._dummy_team = dummy_team

    def setup_team(self, team_members):
        return self._dummy_team

    def total_cost(self):
        return 0

@pytest.fixture
def dummy_team():
    # Create a dummy Team with a single mate "mate1"
    return Team(providers={}, llms={"mate1": None})

@pytest.fixture
def dummy_prompt(tmp_path: Path):
    # Create a temporary prompt file to act as the source.
    prompt_file = tmp_path / "loopflow.md"
    prompt_file.write_text(
        "# Test Prompt\n\n"
        "## Goal\nTest goal\n\n"
        "## Output\ntest_output.py\n\n"
        "## Team\n- mate1"
    )
    # Create a Prompt object and assign the _source_path (used when appending clarifications/reviews)
    prompt = Prompt(
        path=prompt_file,
        goal="Test goal",
        output_files=[tmp_path / "test_output.py"],
        team=["mate1"]
    )
    return prompt

@pytest.fixture
def dummy_session(tmp_path: Path, dummy_team: Team, mock_user):
    # Create a dummy session with a dummy user and temp directory.
    return DummySession(user=mock_user, temp_dir=tmp_path, dummy_team=dummy_team)

# --- ClarifyPipeline Test ---
@pytest.mark.asyncio
async def test_clarify_pipeline(dummy_session, dummy_prompt):
    from loopflow.compose.job import Clarify
    async def dummy_clarify_execute(self, **kwargs):  # note the "self" parameter
        return {"questions": {"mate1": "What is the requirement?"}, "team": dummy_session._dummy_team}
    orig_execute = Clarify.execute
    Clarify.execute = dummy_clarify_execute
    try:
        pipeline = ClarifyPipeline(dummy_session, dummy_prompt)
        result = await pipeline.execute()
        assert result["status"] == "success", result
        assert "questions" in result
        # Verify that clarifications have been appended to the prompt file.
        content = dummy_prompt.path.read_text()
        assert "### mate1's questions" in content
        assert "What is the requirement?" in content
    finally:
        Clarify.execute = orig_execute

# --- MatePipeline Test ---
@pytest.mark.asyncio
async def test_mate_pipeline(dummy_session, dummy_prompt):
    from loopflow.compose.job import Draft
    async def dummy_draft_execute(self, **kwargs):  # add "self"
        output_file = dummy_prompt.output_files[0]
        return {"drafts": {"mate1": {output_file: "dummy draft content"}},
                "team": dummy_session._dummy_team,
                "team_members": ["mate1"]}
    orig_execute = Draft.execute
    Draft.execute = dummy_draft_execute
    try:
        pipeline = MatePipeline(dummy_session, dummy_prompt, mate_name="mate1")
        result = await pipeline.execute()
        assert result["status"] == "success"
        # Verify that the output file now contains the draft content.
        output_file = dummy_prompt.output_files[0]
        written_content = output_file.read_text()
        assert "dummy draft content" in written_content
    finally:
        Draft.execute = orig_execute

# --- ReviewPipeline Test ---
@pytest.mark.asyncio
async def test_review_pipeline(dummy_session, dummy_prompt):
    # Create an output file with some existing content.
    output_file = dummy_prompt.output_files[0]
    output_file.write_text("original content")
    from loopflow.compose.job import Review
    async def dummy_review_execute(self, **kwargs):  # add "self"
        return {"reviews": {"mate1": {"user": "dummy review content"}},
                "team": dummy_session._dummy_team}
    orig_execute = Review.execute
    Review.execute = dummy_review_execute
    try:
        pipeline = ReviewPipeline(dummy_session, dummy_prompt)
        result = await pipeline.execute()
        assert result["status"] == "success"
        # Verify that the prompt file now has appended review content.
        content = dummy_prompt.path.read_text()
        assert "### mate1's review" in content
        assert "dummy review content" in content
    finally:
        Review.execute = orig_execute

# --- TeamPipeline Test ---
@pytest.mark.asyncio
async def test_team_pipeline(dummy_session, dummy_prompt):
    from loopflow.compose.job import Draft, Review, Synthesize
    output_file = dummy_prompt.output_files[0]
    async def dummy_draft_execute(self, **kwargs):  # add "self"
        return {"drafts": {"mate1": {output_file: "draft content"}},
                "team": dummy_session._dummy_team,
                "team_members": ["mate1"]}
    async def dummy_review_execute(self, **kwargs):  # add "self"
        return {"reviews": {"mate1": {"mate1": "review content"}},
                "team": dummy_session._dummy_team}
    async def dummy_synthesize_execute(self, **kwargs):  # add "self"
        return {"outputs": {output_file: "final synthesized content"}, "synthesizer": "mate1"}
    orig_draft = Draft.execute
    orig_review = Review.execute
    from loopflow.compose.job import Synthesize
    orig_synthesize = Synthesize.execute
    Draft.execute = dummy_draft_execute
    Review.execute = dummy_review_execute
    Synthesize.execute = dummy_synthesize_execute
    try:
        pipeline = TeamPipeline(dummy_session, dummy_prompt)
        result = await pipeline.execute()
        assert result["status"] == "success"
        assert result["draft_count"] > 0
        assert result["review_count"] > 0
        assert result["file_count"] == 1
        # Verify that the output file now contains the synthesized content.
        written_content = output_file.read_text()
        assert "final synthesized content" in written_content
    finally:
        Draft.execute = orig_draft
        Review.execute = orig_review
        Synthesize.execute = orig_synthesize
