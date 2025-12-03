"""
E2E test utilities for managing real server lifecycle
"""
import subprocess
import time
import httpx
from contextlib import contextmanager


class ServerManager:
    """Manages a real uvicorn server process for E2E testing"""
    
    def __init__(self, host="127.0.0.1", port=8000, startup_timeout=5):
        self.host = host
        self.port = port
        self.startup_timeout = startup_timeout
        self.process = None
        self.base_url = f"http://{host}:{port}"
    
    def start(self):
        """Start the server in a subprocess"""
        self.process = subprocess.Popen(
            ["uvicorn", "src.main:app", "--host", self.host, "--port", str(self.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < self.startup_timeout:
            try:
                response = httpx.get(f"{self.base_url}/")
                if response.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.RequestError):
                time.sleep(0.1)
        
        # If we get here, server didn't start
        self.stop()
        raise RuntimeError(f"Server failed to start within {self.startup_timeout} seconds")
    
    def stop(self):
        """Stop the server process"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            
            # Capture output for debugging
            stdout, stderr = self.process.communicate() if self.process.poll() is None else ("", "")
            self.process = None
            return stdout, stderr
    
    def is_running(self):
        """Check if server is running"""
        return self.process is not None and self.process.poll() is None


@contextmanager
def running_server(host="127.0.0.1", port=8000):
    """Context manager for running server during tests"""
    server = ServerManager(host, port)
    try:
        server.start()
        yield server
    finally:
        server.stop()
