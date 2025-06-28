```python
import os
import tempfile
import unittest
from pathlib import Path

from codeflow.io.file import CodeflowIgnore

class TestCodeflowIgnore(unittest.TestCase):
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

    def test_ignore_patterns(self):
        lf_ignore = CodeflowIgnore(self.base_path)
        lf_ignore.load_ignore_files()

        # Paths that should be ignored
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "test.pyc"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "lib.so"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "subdir/nested.pyc"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "build/lib.so"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "dist/dist.so"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "wandb/data.txt"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "train_dir/model.pt"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "outputs/output.log"))
        self.assertTrue(lf_ignore.is_ignored(self.base_path / "cython_debug/debug.log"))

        # Paths that should not be ignored
        self.assertFalse(lf_ignore.is_ignored(self.base_path / "test.py"))
        self.assertFalse(lf_ignore.is_ignored(self.base_path / "subdir/nested.py"))
        self.assertFalse(lf_ignore.is_ignored(self.base_path / "subdir/special.py"))
        self.assertFalse(lf_ignore.is_ignored(self.base_path / "subdir/special.txt"))

if __name__ == "__main__":
    unittest.main()
```