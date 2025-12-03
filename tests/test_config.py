"""
Tests for configuration module
"""
import pytest
from pathlib import Path
from src.config import config


def test_get_projects_dir():
    """Test get_projects_dir returns correct path"""
    projects_dir = config.get_projects_dir()
    assert projects_dir.name == "projects"
    assert "data" in str(projects_dir)


def test_get_storage_dir():
    """Test get_storage_dir returns correct path"""
    storage_dir = config.get_storage_dir()
    assert storage_dir.name == "storage"


def test_get_project_dir():
    """Test get_project_dir builds correct path"""
    project_dir = config.get_project_dir("test")
    assert project_dir.name == "test"
    assert project_dir.parent.name == "projects"


def test_get_project_dir_case_insensitive():
    """Test project dir is case-insensitive"""
    assert config.get_project_dir("TEST") == config.get_project_dir("test")
    assert config.get_project_dir("TeSt") == config.get_project_dir("test")


def test_get_project_prompts_dir():
    """Test get_project_prompts_dir builds correct path"""
    prompts_dir = config.get_project_prompts_dir("test")
    assert prompts_dir.name == "prompts"
    assert prompts_dir.parent.name == "test"


def test_get_user_workspace_dir():
    """Test get_user_workspace_dir builds correct path"""
    workspace = config.get_user_workspace_dir("user1", "test")
    assert workspace.name == "test"
    assert workspace.parent.name == "user1"
    assert workspace.parent.parent.name == "storage"


def test_get_user_workspace_dir_case_insensitive():
    """Test user workspace is case-insensitive"""
    w1 = config.get_user_workspace_dir("USER", "PROJECT")
    w2 = config.get_user_workspace_dir("user", "project")
    assert w1 == w2


def test_list_available_projects():
    """Test list_available_projects returns project directories"""
    projects = config.list_available_projects()
    assert isinstance(projects, list)
    # At minimum, test project should exist
    assert "test" in projects


def test_project_exists():
    """Test project_exists checks directory existence"""
    # Should exist (created during data migration)
    assert config.project_exists("test") == True
    
    # Should not exist
    assert config.project_exists("nonexistent") == False


def test_project_exists_case_insensitive():
    """Test project_exists is case-insensitive"""
    assert config.project_exists("TEST") == config.project_exists("test")
    assert config.project_exists("TeSt") == config.project_exists("test")
