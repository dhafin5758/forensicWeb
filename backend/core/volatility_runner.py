"""
Volatility 3 Plugin Runner - Production Implementation
Executes Volatility 3 plugins programmatically with robust error handling,
timeout management, and structured output normalization.
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict
from enum import Enum

from backend.config import settings


logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    """Plugin execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class PluginExecutionResult:
    """Structured result from a plugin execution."""
    plugin_name: str
    status: PluginStatus
    started_at: datetime
    completed_at: Optional[datetime]
    execution_time_seconds: float
    row_count: int
    output_json_path: Optional[Path]
    parsed_data: Optional[List[Dict[str, Any]]]
    error_message: Optional[str]
    stderr: Optional[str]
    returncode: int


class Volatility3Runner:
    """
    Production-grade Volatility 3 plugin executor.
    
    Responsibilities:
    - Execute plugins via subprocess with isolation
    - Enforce timeouts and resource limits
    - Capture and normalize JSON output
    - Handle errors and edge cases
    - Support both sync and async execution
    """
    
    def __init__(
        self,
        memory_image_path: Path,
        output_dir: Path,
        timeout_seconds: int = None
    ):
        """
        Initialize the runner.
        
        Args:
            memory_image_path: Path to the memory dump file
            output_dir: Directory for storing plugin outputs
            timeout_seconds: Maximum execution time per plugin
        """
        self.memory_image_path = Path(memory_image_path)
        self.output_dir = Path(output_dir)
        self.timeout_seconds = timeout_seconds or settings.VOL3_TIMEOUT_SECONDS
        
        # Validate inputs
        if not self.memory_image_path.exists():
            raise FileNotFoundError(f"Memory image not found: {self.memory_image_path}")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify vol3 is available
        self._verify_volatility_installation()
    
    def _verify_volatility_installation(self) -> None:
        """Verify that Volatility 3 is installed and accessible."""
        try:
            result = subprocess.run(
                [settings.VOL3_PATH, "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"Volatility 3 check failed: {result.stderr}")
            logger.info("Volatility 3 verified at: %s", settings.VOL3_PATH)
        except FileNotFoundError:
            raise RuntimeError(
                f"Volatility 3 not found at {settings.VOL3_PATH}. "
                "Set VOL3_PATH in configuration."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Volatility 3 verification timed out")
    
    def execute_plugin(
        self,
        plugin_name: str,
        extra_args: Optional[List[str]] = None
    ) -> PluginExecutionResult:
        """
        Execute a single Volatility plugin synchronously.
        
        Args:
            plugin_name: Name of the plugin (e.g., 'windows.pslist')
            extra_args: Additional plugin-specific arguments
        
        Returns:
            PluginExecutionResult with execution details
        """
        started_at = datetime.utcnow()
        output_file = self.output_dir / f"{plugin_name.replace('.', '_')}.json"
        
        # Build command
        cmd = self._build_command(plugin_name, output_file, extra_args)
        
        logger.info(
            "Executing plugin '%s' on %s",
            plugin_name,
            self.memory_image_path.name
        )
        
        try:
            # Execute with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.output_dir
            )
            
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Parse output
            parsed_data, row_count = self._parse_json_output(output_file)
            
            # Determine status
            if result.returncode == 0 and parsed_data is not None:
                status = PluginStatus.SUCCESS
                error_message = None
            else:
                status = PluginStatus.FAILED
                error_message = self._extract_error_message(result.stderr)
            
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                execution_time_seconds=execution_time,
                row_count=row_count,
                output_json_path=output_file if output_file.exists() else None,
                parsed_data=parsed_data,
                error_message=error_message,
                stderr=result.stderr if result.stderr else None,
                returncode=result.returncode
            )
        
        except subprocess.TimeoutExpired as e:
            logger.error(
                "Plugin '%s' timed out after %d seconds",
                plugin_name,
                self.timeout_seconds
            )
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=PluginStatus.TIMEOUT,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_seconds=self.timeout_seconds,
                row_count=0,
                output_json_path=None,
                parsed_data=None,
                error_message=f"Execution timed out after {self.timeout_seconds}s",
                stderr=str(e.stderr) if e.stderr else None,
                returncode=-1
            )
        
        except Exception as e:
            logger.exception("Unexpected error executing plugin '%s'", plugin_name)
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=PluginStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_seconds=(datetime.utcnow() - started_at).total_seconds(),
                row_count=0,
                output_json_path=None,
                parsed_data=None,
                error_message=str(e),
                stderr=None,
                returncode=-1
            )
    
    async def execute_plugin_async(
        self,
        plugin_name: str,
        extra_args: Optional[List[str]] = None
    ) -> PluginExecutionResult:
        """
        Execute a plugin asynchronously (non-blocking).
        
        Uses asyncio subprocess for concurrent execution.
        """
        started_at = datetime.utcnow()
        output_file = self.output_dir / f"{plugin_name.replace('.', '_')}.json"
        
        cmd = self._build_command(plugin_name, output_file, extra_args)
        
        logger.info("Executing plugin '%s' (async)", plugin_name)
        
        try:
            # Create async subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.output_dir)
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise subprocess.TimeoutExpired(cmd, self.timeout_seconds)
            
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Parse output
            parsed_data, row_count = self._parse_json_output(output_file)
            
            status = PluginStatus.SUCCESS if process.returncode == 0 else PluginStatus.FAILED
            error_message = None if status == PluginStatus.SUCCESS else self._extract_error_message(
                stderr.decode('utf-8', errors='replace')
            )
            
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                execution_time_seconds=execution_time,
                row_count=row_count,
                output_json_path=output_file if output_file.exists() else None,
                parsed_data=parsed_data,
                error_message=error_message,
                stderr=stderr.decode('utf-8', errors='replace') if stderr else None,
                returncode=process.returncode
            )
        
        except subprocess.TimeoutExpired:
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=PluginStatus.TIMEOUT,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_seconds=self.timeout_seconds,
                row_count=0,
                output_json_path=None,
                parsed_data=None,
                error_message=f"Execution timed out after {self.timeout_seconds}s",
                stderr=None,
                returncode=-1
            )
        
        except Exception as e:
            logger.exception("Async execution failed for plugin '%s'", plugin_name)
            return PluginExecutionResult(
                plugin_name=plugin_name,
                status=PluginStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_seconds=(datetime.utcnow() - started_at).total_seconds(),
                row_count=0,
                output_json_path=None,
                parsed_data=None,
                error_message=str(e),
                stderr=None,
                returncode=-1
            )
    
    def _build_command(
        self,
        plugin_name: str,
        output_file: Path,
        extra_args: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build the Volatility command line.
        
        Format: vol -f <image> -r json -o <output_dir> <plugin> [args]
        """
        cmd = [
            settings.VOL3_PATH,
            "-f", str(self.memory_image_path),
            "-r", "json",  # Renderer: JSON format
            plugin_name
        ]
        
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd
    
    def _parse_json_output(self, output_file: Path) -> tuple[Optional[List[Dict]], int]:
        """
        Parse Volatility JSON output.
        
        Returns:
            (parsed_data, row_count)
        """
        if not output_file.exists():
            return None, 0
        
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                # Volatility outputs JSONL (one JSON object per line)
                lines = f.readlines()
                
                if not lines:
                    return None, 0
                
                parsed_rows = []
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            parsed_rows.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning("Skipping malformed JSON line: %s", line[:100])
                
                return parsed_rows, len(parsed_rows)
        
        except Exception as e:
            logger.error("Failed to parse JSON output from %s: %s", output_file, e)
            return None, 0
    
    def _extract_error_message(self, stderr: str) -> str:
        """Extract a meaningful error message from stderr."""
        if not stderr:
            return "Unknown error"
        
        # Common Volatility error patterns
        error_patterns = [
            "Unable to validate the plugin requirements",
            "No such file or directory",
            "Unable to determine symbol table",
            "Unsatisfied requirement plugins",
            "No valid profile found",
        ]
        
        for pattern in error_patterns:
            if pattern in stderr:
                return stderr[:500]  # Truncate long errors
        
        # Return first meaningful line
        lines = [l.strip() for l in stderr.split('\n') if l.strip()]
        return lines[0][:500] if lines else "Execution failed"
    
    async def execute_plugin_batch(
        self,
        plugin_names: List[str],
        concurrent: bool = True,
        max_concurrent: int = 3
    ) -> Dict[str, PluginExecutionResult]:
        """
        Execute multiple plugins, optionally in parallel.
        
        Args:
            plugin_names: List of plugin names to execute
            concurrent: Whether to run plugins concurrently
            max_concurrent: Maximum number of concurrent executions
        
        Returns:
            Dictionary mapping plugin names to results
        """
        if not concurrent:
            # Sequential execution
            results = {}
            for plugin_name in plugin_names:
                results[plugin_name] = await self.execute_plugin_async(plugin_name)
            return results
        
        # Parallel execution with semaphore
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(plugin_name: str) -> tuple[str, PluginExecutionResult]:
            async with semaphore:
                result = await self.execute_plugin_async(plugin_name)
                return plugin_name, result
        
        tasks = [execute_with_semaphore(name) for name in plugin_names]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert to dictionary
        results = {}
        for item in results_list:
            if isinstance(item, Exception):
                logger.error("Plugin execution raised exception: %s", item)
            else:
                plugin_name, result = item
                results[plugin_name] = result
        
        return results


class ProfileDetector:
    """
    Detect the OS profile of a memory image.
    
    Uses Volatility's banners plugin or ISF auto-detection.
    """
    
    def __init__(self, memory_image_path: Path):
        self.memory_image_path = Path(memory_image_path)
    
    async def detect_profile(self) -> Dict[str, Any]:
        """
        Detect OS and profile information.
        
        Returns:
            {
                'os': 'Windows' | 'Linux' | 'macOS' | 'Unknown',
                'profile': '<detected profile>',
                'confidence': 0.0-1.0,
                'method': 'banners' | 'isf' | 'manual'
            }
        """
        logger.info("Detecting profile for %s", self.memory_image_path)
        
        # Try banners plugin first
        try:
            cmd = [
                settings.VOL3_PATH,
                "-f", str(self.memory_image_path),
                "banners.Banners"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30
            )
            
            output = stdout.decode('utf-8', errors='replace')
            
            # Parse banners output for OS detection
            os_type = self._parse_banners_output(output)
            
            return {
                'os': os_type,
                'profile': 'auto',  # Vol3 uses ISF auto-detection
                'confidence': 0.8 if os_type != 'Unknown' else 0.3,
                'method': 'banners'
            }
        
        except Exception as e:
            logger.warning("Profile detection failed: %s", e)
            return {
                'os': 'Unknown',
                'profile': 'auto',
                'confidence': 0.0,
                'method': 'fallback'
            }
    
    def _parse_banners_output(self, output: str) -> str:
        """Parse banners output to determine OS type."""
        output_lower = output.lower()
        
        if 'windows' in output_lower or 'microsoft' in output_lower:
            return 'Windows'
        elif 'linux' in output_lower:
            return 'Linux'
        elif 'darwin' in output_lower or 'macos' in output_lower:
            return 'macOS'
        else:
            return 'Unknown'
