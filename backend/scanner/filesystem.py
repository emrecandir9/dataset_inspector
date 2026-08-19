"""Dataset Inspector - Filesystem scanner.

Performs a fast walk of the dataset directory to gather structural
information without reading file contents.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from backend.core.config import config
from backend.core.exceptions import PathNotFoundError, ScanError
from backend.core.models import (
    DirectoryInfo,
    ExtensionCount,
    FileInfo,
    ScanResult,
)


def scan_directory(root_path: str | Path) -> ScanResult:
    """Scan a directory and return structural information.
    
    This is the first stage of the pipeline. It does NOT read file contents,
    only gathers filesystem metadata (names, sizes, extensions, structure).
    
    Args:
        root_path: Path to the dataset root directory.
        
    Returns:
        ScanResult with complete filesystem metadata.
        
    Raises:
        PathNotFoundError: If the path does not exist.
        ScanError: If scanning fails.
    """
    root = Path(root_path).resolve()
    
    if not root.exists():
        raise PathNotFoundError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise ScanError(f"Path is not a directory: {root}")
    
    total_files = 0
    total_directories = 0
    total_size = 0
    extension_counter: Counter[str] = Counter()
    extension_sizes: Counter[str] = Counter()
    empty_dirs: list[str] = []
    hidden_files: list[str] = []
    symlinks: list[str] = []
    file_list: list[FileInfo] = []
    
    try:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            rel_dir = os.path.relpath(dirpath, root)
            dir_name = os.path.basename(dirpath)
            
            # Skip ignored directories
            dirnames[:] = [
                d for d in dirnames
                if d not in config.ignore_patterns and not d.startswith(".")
            ]
            
            total_directories += 1
            
            if not filenames and not dirnames:
                empty_dirs.append(os.path.relpath(dirpath, root))
            
            for filename in filenames:
                # Skip ignored files
                if filename in config.ignore_patterns:
                    continue
                    
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, root)
                
                # Check symlink
                is_symlink = os.path.islink(filepath)
                if is_symlink:
                    symlinks.append(rel_path)
                
                # Check hidden
                is_hidden = filename.startswith(".")
                if is_hidden:
                    hidden_files.append(rel_path)
                    continue  # Don't count hidden files in stats
                
                # Get file info
                try:
                    stat = os.stat(filepath)
                    size = stat.st_size
                except OSError:
                    size = 0
                
                ext = os.path.splitext(filename)[1].lower()
                
                total_files += 1
                total_size += size
                extension_counter[ext] += 1
                extension_sizes[ext] += size
                
                file_info = FileInfo(
                    path=rel_path,
                    name=filename,
                    extension=ext,
                    size_bytes=size,
                    is_hidden=is_hidden,
                    is_symlink=is_symlink,
                )
                file_list.append(file_info)
    
    except PermissionError as e:
        raise ScanError(f"Permission denied: {e}")
    except OSError as e:
        raise ScanError(f"OS error during scan: {e}")
    
    # Build extension counts sorted by frequency
    extensions = [
        ExtensionCount(
            extension=ext if ext else "(no extension)",
            count=count,
            total_size_bytes=extension_sizes[ext],
        )
        for ext, count in extension_counter.most_common()
    ]
    
    # Build directory tree (limited depth)
    directory_tree = _build_tree(root, root, depth=0)
    
    return ScanResult(
        root_path=str(root),
        total_files=total_files,
        total_directories=total_directories,
        total_size_bytes=total_size,
        extensions=extensions,
        directory_tree=directory_tree,
        empty_directories=empty_dirs,
        hidden_files=hidden_files,
        symlinks=symlinks,
        file_list=file_list,
    )


def _build_tree(
    path: Path,
    root: Path,
    depth: int,
) -> DirectoryInfo:
    """Build a directory tree structure (limited depth)."""
    children: list[DirectoryInfo | FileInfo] = []
    num_files = 0
    num_subdirs = 0
    total_size = 0
    
    if depth >= config.max_file_tree_depth:
        return DirectoryInfo(
            path=str(path.relative_to(root)),
            name=path.name or str(root),
        )
    
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
        
        for entry in entries:
            # Skip ignored
            if entry.name in config.ignore_patterns or entry.name.startswith("."):
                continue
            
            if entry.is_dir(follow_symlinks=False):
                num_subdirs += 1
                child_tree = _build_tree(
                    Path(entry.path), root, depth + 1
                )
                total_size += child_tree.total_size_bytes
                children.append(child_tree)
                
            elif entry.is_file(follow_symlinks=False):
                num_files += 1
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                total_size += size
                
                # Only add individual files to tree at shallow depths
                if depth < 3 and len(children) < 50:
                    children.append(FileInfo(
                        path=str(Path(entry.path).relative_to(root)),
                        name=entry.name,
                        extension=os.path.splitext(entry.name)[1].lower(),
                        size_bytes=size,
                    ))
    except PermissionError:
        pass
    
    rel_path = str(path.relative_to(root)) if path != root else "."
    
    return DirectoryInfo(
        path=rel_path,
        name=path.name or str(root.name),
        num_files=num_files,
        num_subdirs=num_subdirs,
        total_size_bytes=total_size,
        children=children,
    )
