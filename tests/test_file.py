"""Tests for file loading and context utilities."""

import pytest
from pathlib import Path
from loopflow.file import get_code_context_root, resolve_codebase_path, get_context

def _create_files(tmp_path: Path, files: dict[str, str]) -> Path:
    """Creates files with content in the test codebase."""
    for path_str, content in files.items():
        file_path = tmp_path / path_str
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(str(content))
    return tmp_path

@pytest.fixture
def create_test_codebase(tmp_path):
    """
    Fixture to create a test codebase with specified files.
    Returns a function that creates files in the temporary directory.
    """
    return lambda files: _create_files(tmp_path, files)

def test_basic_context_loading(create_test_codebase, monkeypatch):
    """Test basic context file loading."""
    root = create_test_codebase({
        "manabot/manabot/main.py": "print('hello')",
        "manabot/README.md": "# Manabot"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    # Load context in XML format
    content = get_context(["manabot"])
    
    # Basic checks
    assert "<documents>" in content
    assert "README.md" in content
    assert "main.py" in content
    assert "<type>readme</type>" in content
    assert "# Manabot" in content

def test_multiple_path_loading(create_test_codebase, monkeypatch):
    """Test loading multiple paths simultaneously."""
    root = create_test_codebase({
        "manabot/manabot/main.py": "print('manabot')",
        "managym/tests/test_env.py": "def test_env(): pass",
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot", "managym/tests"])
    
    # Verify both sets of files are loaded
    assert "main.py" in content
    assert "test_env.py" in content

def test_extension_filtering(create_test_codebase, monkeypatch):
    """Test filtering files by extension."""
    root = create_test_codebase({
        "manabot/manabot/main.py": "print('hello')",
        "manabot/manabot/config.js": "const config = {};",
        "manabot/README.md": "# Manabot"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot"], extensions=(".py",))
    
    # Verify only .py files are loaded (and READMEs)
    assert "main.py" in content
    assert "config.js" not in content
    assert "README.md" in content  # READMEs are always included

def test_hierarchical_readme_loading(create_test_codebase, monkeypatch):
    """Test loading READMEs from different directory levels."""
    root = create_test_codebase({
        "manabot/manabot/env/data/sample.txt": "data",
        "manabot/manabot/env/README.md": "# Env docs",
        "manabot/README.md": "# Root docs"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot/manabot/env/data"])
    
    # Verify README content and ordering
    root_pos = content.find("# Root docs")
    env_pos = content.find("# Env docs")
    assert root_pos != -1
    assert env_pos != -1
    assert root_pos < env_pos  # Root README should appear first
    assert "sample.txt" in content

def test_direct_path_resolution(create_test_codebase, monkeypatch):
    """Tests that direct paths work without requiring auto-prefixing."""
    root = create_test_codebase({
        "manabot/env/config.py": "settings = {}",
        "manabot/README.md": "# Direct Structure"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot/env"])
    
    assert "config.py" in content
    assert "# Direct Structure" in content

def test_auto_prefixed_path_resolution(create_test_codebase, monkeypatch):
    """Tests that auto-prefixing works when direct path doesn't exist."""
    root = create_test_codebase({
        "manabot/manabot/env/config.py": "settings = {}",
        "manabot/README.md": "# Prefixed Structure"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot/env"])
    
    assert "config.py" in content
    assert "# Prefixed Structure" in content

def test_raw_format(create_test_codebase, monkeypatch):
    """Test raw output format."""
    root = create_test_codebase({
        "manabot/README.md": "# Test README",
        "manabot/main.py": "print('hello')"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot"], raw=True)
    
    # Check raw format markers
    assert "### README START ###" in content
    assert "### README END ###" in content
    assert "---" in content
    
    # Verify no XML tags in raw output
    assert "<document" not in content
    assert "<type>" not in content

def test_gitignore_patterns(create_test_codebase, monkeypatch):
    """Test gitignore pattern matching."""
    root = create_test_codebase({
        "manabot/.gitignore": ".DS_Store\npytest_cache\n*.pyc\n__pycache__",
        "manabot/main.py": "print('hello')",
        "manabot/.DS_Store": "mac file",
        "manabot/test.pyc": "compiled python",
        "manabot/__pycache__/main.cpython-39.pyc": "bytecode",
        "manabot/src/utils.py": "util code"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot"])
    
    # Files that should be included
    assert "main.py" in content
    assert "utils.py" in content
    
    # Files that should be ignored
    assert "__pycache__" not in content
    assert ".pyc" not in content
    assert ".DS_Store" not in content

def test_path_resolution_for_reading(create_test_codebase, monkeypatch):
    """Test path resolution for reading files."""
    root = create_test_codebase({
        "project/config.py": "settings = {}",
        "other/other/main.py": "print('hello')",
    })
    
    resolved_direct = resolve_codebase_path("project/config.py", root=root)
    assert resolved_direct == root / "project/config.py"
    assert resolved_direct.exists()
    
    resolved_doubled = resolve_codebase_path("other/main.py", root=root)
    assert resolved_doubled == root / "other/other/main.py"
    assert resolved_doubled.exists()

def test_path_resolution_for_writing(create_test_codebase, monkeypatch):
    """Test path resolution for writing files."""
    root = create_test_codebase({
        "project/lib/": "",
        "other/other/src/": "",
    })
    
    # Direct path when directory exists
    write_direct = resolve_codebase_path(
        "project/lib/module.py",
        root=root,
        for_reading=False
    )
    assert write_direct == root / "project/lib/module.py"
    assert write_direct.parent.exists()
    
    # Doubled path when directory exists
    write_doubled = resolve_codebase_path(
        "other/src/util.py",
        root=root,
        for_reading=False
    )
    assert write_doubled == root / "other/other/src/util.py"
    assert write_doubled.parent.exists()
    
    # New path
    write_new = resolve_codebase_path(
        "new/code.py",
        root=root,
        for_reading=False
    )
    assert write_new == root / "new/code.py"

def test_code_context_root(monkeypatch):
    """Test CODE_CONTEXT_ROOT environment variable handling."""
    custom_root = Path("/custom/root")
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(custom_root))
    assert get_code_context_root() == custom_root
    
    monkeypatch.delenv("CODE_CONTEXT_ROOT")
    assert get_code_context_root() == Path.home() / "src"

def test_document_indexing(create_test_codebase, monkeypatch):
    """Test that document indices are sequential and properly ordered."""
    root = create_test_codebase({
        "manabot/README.md": "# Root",
        "manabot/src/README.md": "# Src",
        "manabot/src/main.py": "print('hello')",
        "manabot/src/util.py": "# utils"
    })
    
    monkeypatch.setenv("CODE_CONTEXT_ROOT", str(root))
    
    content = get_context(["manabot"])
    
    # Extract indices and verify order
    indices = []
    for line in content.split('\n'):
        if '<document index="' in line:
            idx = int(line.split('"')[1])
            indices.append(idx)
    
    # Verify sequential numbering
    assert indices == list(range(1, len(indices) + 1))
    
    # Verify READMEs come first
    readme_indices = []
    non_readme_indices = []
    is_readme = False
    for line in content.split('\n'):
        if '<document index="' in line:
            idx = int(line.split('"')[1])
            if is_readme:
                readme_indices.append(idx)
            else:
                non_readme_indices.append(idx)
        elif '<type>readme</type>' in line:
            is_readme = True
        elif '</document>' in line:
            is_readme = False
    
    assert all(r < n for r in readme_indices for n in non_readme_indices)