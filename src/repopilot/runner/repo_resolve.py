"""Resolve local paths and git URLs into runnable git repositories (Adhoc Phase C)."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path


def is_repo_url(spec: str) -> bool:
    return spec.startswith(("http://", "https://", "git@", "ssh://", "git://"))


def _cache_key(spec: str) -> str:
    digest = hashlib.sha256(spec.encode()).hexdigest()[:12]
    tail = spec.rstrip("/").split("/")[-1].replace(".git", "")
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", tail)[:32] or "repo"
    return f"{safe}_{digest}"


def clone_repo_url(url: str, cache_root: Path) -> Path:
    """Clone or refresh a cached copy of a remote repository."""
    cache_root = cache_root.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    dest = cache_root / _cache_key(url)
    if dest.is_dir() and (dest / ".git").is_dir():
        subprocess.run(["git", "fetch", "--all", "--prune"], cwd=dest, check=True)
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    subprocess.run(["git", "clone", url, str(dest)], check=True)
    return dest


def materialize_git_repo(source: Path, cache_root: Path) -> Path:
    """Return a git repo path; copy and init when source is not already a repository."""
    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Repository path not found: {source}")
    if (source / ".git").is_dir():
        return source

    cache_root = cache_root.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    dest = cache_root / f"local_{_cache_key(str(source))}"
    if dest.is_dir() and (dest / ".git").is_dir():
        return dest

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        source,
        dest,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv", "venv", "node_modules"),
    )
    subprocess.run(["git", "init"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(["git", "commit", "-m", "adhoc snapshot"], cwd=dest, check=True)
    return dest


def resolve_git_ref(repo_path: Path, ref: str | None) -> str:
    """Resolve ref to a commit SHA; default HEAD of the cached repo."""
    repo_path = repo_path.resolve()
    target = ref or "HEAD"
    result = subprocess.run(
        ["git", "rev-parse", target],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def resolve_repository(spec: str, *, cache_root: Path) -> Path:
    """Resolve a local path or remote URL to a git repository root."""
    if is_repo_url(spec):
        return clone_repo_url(spec, cache_root)
    return materialize_git_repo(Path(spec).expanduser(), cache_root)
