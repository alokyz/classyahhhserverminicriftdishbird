"""Constrained filesystem access for configured Minecraft server files."""

from __future__ import annotations

import os
import stat
from pathlib import Path


class UnsafeServerPath(ValueError):
    """Raised when a requested server path escapes the configured root."""


def resolve_server_root(configured_root: Path | None) -> Path | None:
    if configured_root is None:
        return None
    try:
        root = configured_root.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return root if root.is_dir() else None


def resolve_inside(root: Path, relative_path: str | Path, *, must_exist: bool = True) -> Path:
    """Resolve a relative path and reject traversal and symlink escapes."""
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise UnsafeServerPath("path must remain inside the configured server directory")
    try:
        resolved = (root / relative).resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise UnsafeServerPath("path is unavailable") from exc
    if not resolved.is_relative_to(root):
        raise UnsafeServerPath("path must remain inside the configured server directory")
    return resolved


def _open_directory_beneath(root: Path, relative_path: str | Path) -> int:
    """Open a directory beneath root without following any path symlinks."""
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise UnsafeServerPath("path must remain inside the configured server directory")
    if not root.is_absolute():
        raise UnsafeServerPath("configured server directory must resolve to an absolute path")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise OSError("secure no-follow file access is unavailable on this platform")

    directory_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW | os.O_DIRECTORY
    root_fd = os.open("/", directory_flags)
    active_fd = root_fd
    try:
        # Start at filesystem root and walk the canonical server root one
        # component at a time, rejecting ancestor symlink substitutions too.
        components = [*root.parts[1:], *(part for part in relative.parts if part not in {"", "."})]
        for component in components:
            next_fd = os.open(component, directory_flags, dir_fd=active_fd)
            if active_fd != root_fd:
                os.close(active_fd)
            active_fd = next_fd
        result_fd = os.dup(active_fd) if active_fd == root_fd else active_fd
        if active_fd != root_fd:
            active_fd = -1
        return result_fd
    finally:
        if active_fd >= 0 and active_fd != root_fd:
            os.close(active_fd)
        os.close(root_fd)


def list_regular_files(root: Path, relative_path: str | Path, *, limit: int) -> list[tuple[str, int]]:
    """List regular-file names and sizes without following entry symlinks."""
    directory_fd = _open_directory_beneath(root, relative_path)
    try:
        entries: list[tuple[str, int]] = []
        for name in os.listdir(directory_fd):
            if len(entries) >= limit:
                break
            try:
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode):
                entries.append((name, info.st_size))
        return entries
    finally:
        os.close(directory_fd)


def read_bounded_tail(
    root: Path, relative_path: str | Path, *, max_bytes: int, max_lines: int
) -> list[str]:
    """Read a bounded tail with descriptor-relative, no-follow traversal.

    Every directory and the final file are opened relative to an already-open
    parent descriptor. O_NOFOLLOW rejects symlinks even if a path component is
    replaced after a separate containment check.
    """
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise UnsafeServerPath("path must remain inside the configured server directory")
    parts = [part for part in relative.parts if part not in {"", "."}]
    if not parts:
        raise UnsafeServerPath("a file path is required")

    parent_fd = _open_directory_beneath(root, Path(*parts[:-1]))
    common_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    try:
        file_fd = os.open(
            parts[-1], common_flags | getattr(os, "O_NONBLOCK", 0), dir_fd=parent_fd
        )
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                raise OSError("configured log path is not a regular file")
            os.lseek(file_fd, 0, os.SEEK_END)
            size = os.lseek(file_fd, 0, os.SEEK_CUR)
            os.lseek(file_fd, max(0, size - max_bytes), os.SEEK_SET)
            remaining = max_bytes
            chunks: list[bytes] = []
            while remaining:
                chunk = os.read(file_fd, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        os.close(parent_fd)
    lines = data.decode("utf-8", errors="replace").splitlines()[-max_lines:]
    return ["".join(ch for ch in line if ch.isprintable() or ch == "\t")[:4096] for line in lines]
