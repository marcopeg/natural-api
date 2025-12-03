"""
Configuration management for Codex API
"""
import os
from pathlib import Path
from datetime import datetime


class Config:
    """Application configuration"""
    
    # AI Provider settings
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "codex")
    
    # Workspace directory where AI can create/modify files
    WORKSPACE_DIR: Path = Path(os.getenv("WORKSPACE_DIR", "./data"))
    
    # Logs directory for request/response logging
    LOGS_DIR: Path = WORKSPACE_DIR / "logs"
    
    # Command timeout in seconds
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "60"))
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Logging level
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # OpenAPI toggle
    OPENAPI_ENABLED: bool = os.getenv("OPENAPI_ENABLED", "true").lower() in ("1", "true", "yes")
    
    @classmethod
    def get_workspace_dir(cls) -> Path:
        """Get workspace directory, creating it if it doesn't exist"""
        cls.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        return cls.WORKSPACE_DIR
    

    # Multi-project and multi-user support
    PROJECTS_DIR: Path = WORKSPACE_DIR / "projects"
    STORAGE_DIR: Path = WORKSPACE_DIR / "storage"

    @classmethod
    def get_projects_dir(cls) -> Path:
        """Get projects base directory"""
        return cls.PROJECTS_DIR

    @classmethod
    def get_storage_dir(cls) -> Path:
        """Get storage base directory"""
        return cls.STORAGE_DIR

    @classmethod
    def get_project_dir(cls, project_id: str) -> Path:
        """Get project directory (not creating it)"""
        return cls.PROJECTS_DIR / project_id.lower()

    @classmethod
    def get_project_prompts_dir(cls, project_id: str) -> Path:
        """Get project's prompts directory"""
        return cls.get_project_dir(project_id) / "prompts"

    @classmethod
    def get_user_workspace_dir(cls, user_id: str, project_id: str) -> Path:
        """Get user's workspace directory for a specific project"""
        return cls.STORAGE_DIR / user_id.lower() / project_id.lower()

    @classmethod
    def list_available_projects(cls) -> list[str]:
        """List all available projects"""
        if not cls.PROJECTS_DIR.exists():
            return []
        return sorted([d.name for d in cls.PROJECTS_DIR.iterdir() if d.is_dir()])

    @classmethod
    def project_exists(cls, project_id: str) -> bool:
        """Check if project directory exists"""
        return cls.get_project_dir(project_id).exists()

    @classmethod
    def get_logs_dir(cls) -> Path:
        """Get logs directory, creating it if it doesn't exist"""
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        return cls.LOGS_DIR

    @classmethod
    def get_log_file_path(cls, timestamp: datetime, status_code: int, file_request_id: str | None = None) -> Path:
        """
        Get full path for log file, creating parent directories.
        
        Args:
            timestamp: UTC timestamp for the log
            status_code: HTTP status code
            file_request_id: Optional custom request ID for filename (uses timestamp if not provided)
            
        Returns:
            Path: Full path to log file (logs/YYYY/MM/DD/{file_request_id}-{code}.md)
        """
        from src.logging.timestamp import format_filename_timestamp, format_folder_path
        
        folder_path = cls.LOGS_DIR / format_folder_path(timestamp)
        folder_path.mkdir(parents=True, exist_ok=True)
        
        if file_request_id:
            filename = f"{file_request_id}-{status_code}.md"
        else:
            filename = f"{format_filename_timestamp(timestamp)}-{status_code}.md"
        return folder_path / filename


# Global config instance
config = Config()
