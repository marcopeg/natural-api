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
            
            # Stream output live while capturing it
            import sys
            import threading

            proc = subprocess.Popen(
                cmd,
                cwd=str(self.workspace_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # line-buffered
            )

            stdout_lines: list[str] = []
            stderr_lines: list[str] = []

            def _reader(stream, sink, collector):
                try:
                    for line in iter(stream.readline, ''):
                        sink.write(line)
                        sink.flush()
                        collector.append(line)
                finally:
                    try:
                        stream.close()
                    except Exception:
                        pass

            t_out = threading.Thread(target=_reader, args=(proc.stdout, sys.stdout, stdout_lines))
            t_err = threading.Thread(target=_reader, args=(proc.stderr, sys.stderr, stderr_lines))
            t_out.daemon = True
            t_err.daemon = True
            t_out.start()
            t_err.start()

            try:
                returncode = proc.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                # Kill process on timeout
                proc.kill()
                try:
                    proc.communicate(timeout=2)
                except Exception:
                    pass
                print("[CodexProvider] --- Output End ---")
                print(f"[CodexProvider] Exit code: 124 (timeout)\n")
                return AIProviderResult(
                    stdout=''.join(stdout_lines),
                    stderr=''.join(stderr_lines) + ("\n" if stderr_lines else "") + "[ERROR] Codex execution timed out",
                    returncode=124,
                    success=False,
                    command=command_string,
                    error_message=f"Codex execution exceeded timeout of {self.timeout} seconds"
                )

            # Ensure readers finish
            t_out.join(timeout=2)
            t_err.join(timeout=2)

            print("[CodexProvider] --- Output End ---")
            print(f"[CodexProvider] Exit code: {returncode}\n")

            stdout_text = ''.join(stdout_lines)
            stderr_text = ''.join(stderr_lines)

            return AIProviderResult(
                stdout=stdout_text,
                stderr=stderr_text,
                returncode=returncode,
                success=returncode == 0,
                command=command_string,
                error_message=None if returncode == 0 else "Codex execution failed"
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
