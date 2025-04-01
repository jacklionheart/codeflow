"""
File loading and context extraction utilities.

Provides methods for collecting and formatting files from different project structures,
with special handling for READMEs and support for both XML and raw output formats.
"""

import os
from pathlib import Path
from typing import List, Set, Optional, Tuple, Union
from fnmatch import fnmatch
from dataclasses import dataclass
import logging 

logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Represents a file's content and metadata for context output."""
    index: int
    source: str
    content: str
    is_readme: bool = False

def get_code_context_root() -> Path:
    """Return the root directory for code context, defaulting to ~/src."""
    return Path(os.getenv("CODE_CONTEXT_ROOT", str(Path.home() / "src")))

def resolve_codebase_path(
    path_str: Union[str, Path], 
    root: Optional[Path] = None,
    project_dir: Optional[Path] = None,
    for_reading: bool = True
) -> Path:
    """
    Convert path string to an absolute path following codebase conventions.
    
    Args:
        path_str: Path to resolve
        root: Root directory for global paths (defaults to get_code_context_root())
        project_dir: Project directory for relative paths (overrides root)
        for_reading: Whether path is for reading (vs writing)
    
    Returns:
        Resolved absolute path
    """
    if root is None:
        root = get_code_context_root()

    path_obj = Path(str(path_str))
    
    # If path is absolute, just return it
    if path_obj.is_absolute():
        return path_obj.resolve()
    
    # If project_dir is specified, use that as the base for relative paths
    if project_dir is not None:
        result = (project_dir / path_obj).resolve()
        return result
    
    # Otherwise use the traditional code context resolution
    dirpath = path_obj.parent
    filename = path_obj.name
    direct_path = (root / path_obj).resolve()

    if len(dirpath.parts) > 0:
        doubled_path = (root / dirpath.parts[0] / dirpath.parts[0] / Path(*dirpath.parts[1:]) / filename).resolve()
    else:
        doubled_path = direct_path

    if for_reading:
        direct_exists = direct_path.exists()
        doubled_exists = doubled_path.exists()
        result = direct_path 
        if doubled_exists and not direct_exists:
            result = doubled_path
        return result
    else:
        doubled_exists = doubled_path.parent.exists()
        if doubled_exists:
            result = doubled_path
        else:
            result = direct_path
        return result

def _find_parent_readmes(path: Path, context_root: Optional[Path] = None) -> List[Path]:
    """
    Find all README.md files from given path up to context root.
    
    Args:
        path: Path to start from
        context_root: Root directory to stop at (defaults to CODE_CONTEXT_ROOT)
    
    Returns:
        List of README paths
    """
    readmes = []
    current = path
    root = context_root or get_code_context_root()

    # Go up the directory tree until we reach the root or can't go higher
    while current != root and current != current.parent:
        readme_path = current / "README.md"
        if readme_path.exists():
            readmes.append(readme_path)
        current = current.parent

    # Add root README if it exists
    root_readme = root / "README.md"
    if root_readme.exists() and root_readme not in readmes:
        readmes.append(root_readme)

    # Sort by depth and path
    readmes.sort(key=lambda p: (len(p.parts), str(p)))
    return readmes

def _should_ignore(path: str, gitignore_rules: List[str], root_dir: str) -> bool:
    """Check if path should be ignored according to gitignore patterns."""
    rel_path = os.path.relpath(path, root_dir)
    basename = os.path.basename(path)

    for rule in gitignore_rules:
        if fnmatch(basename, rule) or fnmatch(rel_path, rule):
            return True
        if os.path.isdir(path) and (fnmatch(basename + "/", rule) or fnmatch(rel_path + "/", rule)):
            return True
    return False

def _is_binary_path(path: str) -> bool:
    """Check if a file path likely contains binary content."""
    binary_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
        '.exe', '.bin', '.pkl', '.pickle',
        '.zip', '.tar', '.gz', '.jpg', '.png', '.gif'
    }
    return any(path.endswith(ext) for ext in binary_extensions)

def _load_file(
    path: str,
    index: int,
    processed_files: Set[str],
    extensions: Optional[Tuple[str, ...]] = None
) -> Optional[Document]:
    """Load a single file into a Document if it meets criteria."""
    if path in processed_files:
        return None
    if extensions and not (path.endswith("README.md") or any(path.endswith(ext) for ext in extensions)):
        return None
    if _is_binary_path(path):
        print(f"Warning: Skipping binary file {path}")
        return None

    try:
        with open(path, "r", encoding='utf-8') as f:
            return Document(
                index=index,
                source=path,
                content=f.read(),
                is_readme=path.endswith("README.md")
            )
    except UnicodeDecodeError:
        print(f"Warning: Skipping file {path} due to UnicodeDecodeError")
        return None
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def _collect_files(
    path: str,
    gitignore_rules: List[str],
    processed_files: Set[str],
    next_index: int,
    extensions: Optional[Tuple[str, ...]] = None
) -> List[Document]:
    """Recursively collect files into Document objects."""
    documents = []
    current_index = next_index
    path_obj = Path(path)
    gitignore_root = str(path_obj if path_obj.is_dir() else path_obj.parent)

    def process_file(file_path: str) -> None:
        nonlocal current_index
        if doc := _load_file(file_path, current_index, processed_files, extensions):
            documents.append(doc)
            processed_files.add(file_path)
            current_index += 1

    if path_obj.is_file():
        if not _should_ignore(str(path_obj), gitignore_rules, gitignore_root):
            process_file(str(path_obj))
    elif path_obj.is_dir():
        for root, dirs, files in os.walk(path_obj):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]

            dirs[:] = [d for d in dirs if not _should_ignore(os.path.join(root, d), gitignore_rules, gitignore_root)]
            files = [f for f in files if not _should_ignore(os.path.join(root, f), gitignore_rules, gitignore_root)]

            for file_name in sorted(files):
                process_file(os.path.join(root, file_name))

    return documents

def _read_gitignore(path: str) -> List[str]:
    """Return lines from .gitignore for ignoring certain files/directories."""
    gitignore_path = os.path.join(path, ".gitignore")
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r") as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception:
            return []
    return []

def _format_document(doc: Document, raw: bool) -> str:
    """Format a document according to output format."""
    if raw:
        lines = [doc.source, "---"]
        if doc.is_readme:
            lines.append("### README START ###")
        lines.append(doc.content)
        if doc.is_readme:
            lines.append("### README END ###")
        lines.append("---")
    else:
        lines = [
            f'<document index="{doc.index}">',
            f"<source>{doc.source}</source>"
        ]
        if doc.is_readme:
            lines.extend([
                "<type>readme</type>",
                "<instructions>",
                doc.content,
                "</instructions>"
            ])
        else:
            lines.extend([
                "<document_content>",
                doc.content,
                "</document_content>"
            ])
        lines.append("</document>")
    
    return "\n".join(lines)

def get_context(
    paths: Optional[List[Union[str, Path]]],
    raw: bool = False,
    extensions: Optional[Tuple[str, ...]] = None,
    root: Optional[Path] = None,
    project_dir: Optional[Path] = None
) -> str:
    """
    Load and format context from specified paths.
    
    Args:
        paths: List of paths to load context from, or None for no context
        raw: Whether to use raw format instead of XML
        extensions: Optional tuple of file extensions to filter
        root: Optional root directory (defaults to CODE_CONTEXT_ROOT)
        project_dir: Optional project directory (overrides root)
    
    Returns:
        Formatted context string
    """
    if root is None:
        root = get_code_context_root()

    # Handle empty paths
    if not paths:
        return "" if raw else "<documents></documents>"

    processed_files: Set[str] = set()
    documents = []
    next_index = 1

    for path_str in paths:
        try:
            # Use project_dir if provided, otherwise use root
            path = resolve_codebase_path(
                path_str, 
                root=root, 
                project_dir=project_dir,
                for_reading=True
            )
            
            if not path.exists():
                logger.warning(f"Path does not exist: {path}")
                continue

            # Process parent READMEs first
            for readme_path in _find_parent_readmes(path, context_root=project_dir):
                if doc := _load_file(str(readme_path), next_index, processed_files, extensions):
                    documents.append(doc)
                    processed_files.add(str(readme_path))
                    next_index += 1

            # Process requested path
            gitignore_rules = _read_gitignore(
                str(path) if path.is_dir() else str(path.parent)
            )
            new_docs = _collect_files(
                str(path),
                gitignore_rules,
                processed_files,
                next_index,
                extensions
            )
            next_index += len(new_docs)
            documents.extend(new_docs)

        except Exception as e:
            print(f"Error processing path {path_str}: {e}")

    # Sort documents (READMEs first, then by path)
    documents.sort(key=lambda d: (not d.is_readme, d.source))

    # Re-index documents
    for i, doc in enumerate(documents, 1):
        doc.index = i

    # Generate output
    output_lines = []
    if not raw:
        output_lines.append("<documents>")
    
    for doc in documents:
        output_lines.append(_format_document(doc, raw))
    
    if not raw:
        output_lines.append("</documents>")

    return "\n".join(output_lines)