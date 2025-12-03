"""
Codex CLI provider implementation
"""
import subprocess
import shutil
from pathlib import Path
from src.providers.base import AIProvider, AIProviderResult


class CodexProvider(AIProvider):
    """Provider for Codex CLI (codex exec)"""
    
    @property
    def name(self) -> str:
        return "codex"
    
    def is_available(self) -> bool:
        """Check if codex CLI is available in PATH"""
        return shutil.which("codex") is not None
    
    def execute(self, prompt: str, model: str | None = None, dry_run: bool = False) -> AIProviderResult:
        """
        Execute a prompt using codex exec
        
        Args:
            prompt: The instruction to pass to codex exec
            model: Optional model override (e.g., "gpt-5.1-codex-mini")
            dry_run: If True, return command string without executing
        
        Returns:
            AIProviderResult with execution details
        """
        if not self.is_available():
            return AIProviderResult(
                stdout="",
                stderr="Codex CLI not found in PATH",
                returncode=-1,
                success=False,
                command="codex (not available)",
                error_message="Codex CLI is not installed or not available in PATH"
            )
        try:
            # Build command with model parameter
            cmd = ["codex", "exec", "--sandbox", "workspace-write"]
            
            # Add model flag if specified, otherwise use default
            if model:
                cmd.extend(["--model", model])
            else:
                cmd.extend(["--model", "gpt-5.1-codex-mini"])
            
            cmd.append(prompt)
            
            # Build readable command string
            import shlex
            command_string = " ".join(shlex.quote(arg) for arg in cmd)
            
            # If dry-run, return the command string without executing
            if dry_run:
                return AIProviderResult(
                    stdout=command_string,
                    stderr="",
                    returncode=0,
                    success=True,
                    command=command_string,
                    error_message=None
                )
            
            # Print command being executed
            print(f"\n[CodexProvider] Executing: {' '.join(cmd)}")
            print(f"[CodexProvider] Working directory: {self.workspace_dir}")
            print("[CodexProvider] --- Output Start ---")
            
            # Run and capture output
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace_dir),
                capture_output=True,  # Capture output
                text=True,
                timeout=self.timeout,
            )
            
            # Also print to terminal for debugging
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=__import__('sys').stderr)
            
            print("[CodexProvider] --- Output End ---")
            print(f"[CodexProvider] Exit code: {result.returncode}\n")
            
            return AIProviderResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                success=result.returncode == 0,
                command=command_string,
                error_message=None if result.returncode == 0 else "Codex execution failed"
            )
        except subprocess.TimeoutExpired as e:
            import shlex
            # Build command string for diagnostics
            command_string = " ".join(shlex.quote(arg) for arg in cmd) if 'cmd' in locals() else "codex (timeout before command built)"

            # Normalize possible bytes to strings
            def _to_str(val):
                if val is None:
                    return ""
                if isinstance(val, bytes):
                    try:
                        return val.decode("utf-8", errors="replace")
                    except Exception:
                        return str(val)
                return val

            out = _to_str(getattr(e, "stdout", ""))
            err = _to_str(getattr(e, "stderr", ""))
            if err:
                err = err + "\n[ERROR] Codex execution timed out"
            else:
                err = "[ERROR] Codex execution timed out"

            return AIProviderResult(
                stdout=out,
                stderr=err,
                returncode=124,  # Standard timeout exit code
                success=False,
                command=command_string,
                error_message=f"Codex execution exceeded timeout of {self.timeout} seconds"
            )
        except Exception as e:
            command_string = "codex (error before execution)"
            return AIProviderResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                success=False,
                command=command_string,
                error_message=f"Unexpected error executing Codex: {str(e)}"
            )
