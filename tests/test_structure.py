"""Tests for project folder and file structure."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_FOLDERS = [
    "mcp_server",
    "mcp_server/core",
    "mcp_server/providers",
    "mcp_server/tools",
    "mcp_server/models",
    "mcp_server/config",
    "mcp_server/logging",
    "mcp_server/middleware",
    "mcp_server/exceptions",
    "mcp_server/resources",
    "mcp_server/prompts",
    "mcp_server/auth",
    "mcp_server/dashboard",
    "mcp_server/utils",
    "mcp_server/agent",
    "tests",
    "docs",
    "docker",
    "scripts",
    "sample_data",
]

REQUIRED_FILES = [
    "mcp_server/__init__.py",
    "mcp_server/config/__init__.py",
    "mcp_server/config/settings.py",
    "mcp_server/logging/logger.py",
    "mcp_server/exceptions/__init__.py",
    "mcp_server/models/base.py",
    "mcp_server/providers/base.py",
    "mcp_server/utils/helpers.py",
    "mcp_server/server.py",
    "README.md",
    ".gitignore",
    "requirements.txt",
]

def test_folders_exist():
    missing = [p for p in REQUIRED_FOLDERS if not (ROOT / p).is_dir()]
    assert not missing, f"Missing folders: {missing}"

def test_files_exist():
    missing = [p for p in REQUIRED_FILES if not (ROOT / p).is_file()]
    assert not missing, f"Missing files: {missing}"