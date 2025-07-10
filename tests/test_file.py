import os
import tempfile
import unittest
from pathlib import Path

from codeflow.file import _read_gitignore, _should_ignore

class TestGitignoreHandling(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.test_dir.name)

        structure = {
            "test.py": "",
            "test.pyc": "",
            "lib.so": "",
            "subdir": {
                "nested.py": "",
                "nested.pyc": "",
                "special.txt": "",
                "special.py": "",
                ".gitignore": "!special.py\n*.pyc\n"
            },
            "build": {
                "build.py": "",
                "lib.so": "",
            },
            "dist": {
                "dist.so": "",
            },
            "wandb": {
                "data.txt": "",
            },
            "train_dir": {
                "model.pt": "",
            },
            "outputs": {
                "output.log": "",
            },
            "cython_debug": {
                "debug.log": "",
            },
            ".codeflowignore": "*.pyc\n__pycache__/\n/wandb/\ntrain_dir/\nreplays/\n*.egg-info\n/build/\n/build_debug/\n.DS_Store\n.task\noutputs/\n*.so\ncython_debug\nstats.profile\n/dist/\nplayer/dist/\nplayer/node_modules\n"
        }
        self._create_structure(self.base_path, structure)

    def tearDown(self):
        self.test_dir.cleanup()

    def _create_structure(self, base, structure):
        for name, content in structure.items():
            path = base / name
            if isinstance(content, dict):
                path.mkdir(parents=True, exist_ok=True)
                self._create_structure(path, content)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as f:
                    f.write(content)

    def test_read_gitignore(self):
        """Test reading gitignore patterns from file."""
        gitignore_path = self.base_path / ".codeflowignore"
        rules = _read_gitignore(str(gitignore_path))
        
        # Check that patterns were read correctly
        self.assertIn("*.pyc", rules)
        self.assertIn("__pycache__/", rules)
        self.assertIn("/wandb/", rules)
        self.assertIn("train_dir/", rules)
        self.assertIn("*.so", rules)
        
    def test_should_ignore_patterns(self):
        """Test the ignore logic for various file patterns."""
        gitignore_rules = _read_gitignore(str(self.base_path / ".codeflowignore"))
        
        # Binary files should be ignored due to extension
        self.assertTrue(_should_ignore(self.base_path / "test.pyc", gitignore_rules, self.base_path))
        self.assertTrue(_should_ignore(self.base_path / "lib.so", gitignore_rules, self.base_path))
        self.assertTrue(_should_ignore(self.base_path / "subdir/nested.pyc", gitignore_rules, self.base_path))
        self.assertTrue(_should_ignore(self.base_path / "build/lib.so", gitignore_rules, self.base_path))
        self.assertTrue(_should_ignore(self.base_path / "dist/dist.so", gitignore_rules, self.base_path))
        
        # Data files should be ignored due to extension  
        self.assertTrue(_should_ignore(self.base_path / "outputs/output.log", gitignore_rules, self.base_path))
        self.assertTrue(_should_ignore(self.base_path / "cython_debug/debug.log", gitignore_rules, self.base_path))

        # Paths that should not be ignored
        self.assertFalse(_should_ignore(self.base_path / "test.py", gitignore_rules, self.base_path))
        self.assertFalse(_should_ignore(self.base_path / "subdir/nested.py", gitignore_rules, self.base_path))
        
    def test_readme_never_ignored(self):
        """Test that README.md files are never ignored."""
        gitignore_rules = ["*.md", "README.md"]
        
        # README.md should never be ignored even if explicitly in gitignore
        self.assertFalse(_should_ignore(self.base_path / "README.md", gitignore_rules, self.base_path))
        self.assertFalse(_should_ignore(self.base_path / "subdir/README.md", gitignore_rules, self.base_path))

if __name__ == "__main__":
    unittest.main()