"""
Artifact Post-Processing Module
Executes binwalk and exiftool on extracted forensic artifacts
with secure subprocess handling and structured output normalization.
"""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings


logger = logging.getLogger(__name__)


@dataclass
class BinwalkResult:
    """Structured binwalk analysis result."""
    file_path: Path
    analyzed_at: datetime
    success: bool
    signatures_found: List[Dict[str, Any]]
    extracted_files: List[Path]
    error_message: Optional[str]
    execution_time_seconds: float


@dataclass
class ExiftoolResult:
    """Structured exiftool metadata extraction result."""
    file_path: Path
    analyzed_at: datetime
    success: bool
    metadata: Dict[str, Any]
    file_type: Optional[str]
    error_message: Optional[str]
    execution_time_seconds: float


class BinwalkAnalyzer:
    """
    Execute binwalk on binary artifacts to identify embedded files and firmware.
    
    Production features:
    - Safe subprocess execution with timeouts
    - Automatic extraction management
    - Signature database validation
    - Output normalization to JSON
    """
    
    def __init__(self, extraction_dir: Path):
        """
        Initialize binwalk analyzer.
        
        Args:
            extraction_dir: Directory where binwalk will extract carved files
        """
        self.extraction_dir = Path(extraction_dir)
        self.extraction_dir.mkdir(parents=True, exist_ok=True)
        
        if not settings.BINWALK_ENABLED:
            logger.warning("Binwalk is disabled in configuration")
        
        self._verify_installation()
    
    def _verify_installation(self) -> None:
        """Verify binwalk is installed and accessible."""
        try:
            result = subprocess.run(
                [settings.BINWALK_PATH, "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"Binwalk check failed: {result.stderr}")
            logger.info("Binwalk verified at: %s", settings.BINWALK_PATH)
        except FileNotFoundError:
            raise RuntimeError(
                f"Binwalk not found at {settings.BINWALK_PATH}. "
                "Install with: apt-get install binwalk"
            )
    
    async def analyze_file(
        self,
        file_path: Path,
        extract: bool = True,
        timeout_seconds: int = 300
    ) -> BinwalkResult:
        """
        Analyze a file with binwalk.
        
        Args:
            file_path: Path to the file to analyze
            extract: Whether to extract identified files
            timeout_seconds: Maximum execution time
        
        Returns:
            BinwalkResult with signatures and extracted files
        """
        if not settings.BINWALK_ENABLED:
            return BinwalkResult(
                file_path=file_path,
                analyzed_at=datetime.utcnow(),
                success=False,
                signatures_found=[],
                extracted_files=[],
                error_message="Binwalk is disabled",
                execution_time_seconds=0.0
            )
        
        started_at = datetime.utcnow()
        
        # Create file-specific extraction directory
        extract_dir = self.extraction_dir / f"{file_path.stem}_binwalk"
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        # Build command
        cmd = [settings.BINWALK_PATH]
        
        if extract:
            cmd.extend(["-e", "-C", str(extract_dir)])  # Extract to directory
        
        cmd.append(str(file_path))
        
        logger.info("Running binwalk on %s", file_path.name)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(extract_dir)
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
            
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Parse signatures from output
            signatures = self._parse_binwalk_output(stdout.decode('utf-8', errors='replace'))
            
            # Find extracted files
            extracted_files = []
            if extract and extract_dir.exists():
                extracted_files = list(extract_dir.rglob('*'))
                extracted_files = [f for f in extracted_files if f.is_file()]
            
            return BinwalkResult(
                file_path=file_path,
                analyzed_at=completed_at,
                success=process.returncode == 0,
                signatures_found=signatures,
                extracted_files=extracted_files,
                error_message=None if process.returncode == 0 else stderr.decode('utf-8')[:500],
                execution_time_seconds=execution_time
            )
        
        except asyncio.TimeoutError:
            logger.error("Binwalk analysis timed out for %s", file_path)
            return BinwalkResult(
                file_path=file_path,
                analyzed_at=datetime.utcnow(),
                success=False,
                signatures_found=[],
                extracted_files=[],
                error_message=f"Analysis timed out after {timeout_seconds}s",
                execution_time_seconds=timeout_seconds
            )
        
        except Exception as e:
            logger.exception("Binwalk analysis failed for %s", file_path)
            return BinwalkResult(
                file_path=file_path,
                analyzed_at=datetime.utcnow(),
                success=False,
                signatures_found=[],
                extracted_files=[],
                error_message=str(e),
                execution_time_seconds=(datetime.utcnow() - started_at).total_seconds()
            )
    
    def _parse_binwalk_output(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse binwalk text output into structured signatures.
        
        Output format:
        DECIMAL       HEXADECIMAL     DESCRIPTION
        --------------------------------------------------------------------------------
        0             0x0             PNG image, 1920 x 1080, 8-bit/color RGBA
        41            0x29            Zlib compressed data
        """
        signatures = []
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            # Skip headers and empty lines
            if not line or line.startswith('DECIMAL') or line.startswith('---'):
                continue
            
            # Parse signature line
            parts = line.split(None, 2)  # Split on whitespace, max 3 parts
            if len(parts) >= 3:
                try:
                    decimal_offset = int(parts[0])
                    hex_offset = parts[1]
                    description = parts[2]
                    
                    signatures.append({
                        'offset': decimal_offset,
                        'offset_hex': hex_offset,
                        'description': description
                    })
                except ValueError:
                    continue
        
        return signatures
    
    async def analyze_batch(
        self,
        file_paths: List[Path],
        extract: bool = True,
        max_concurrent: int = 2
    ) -> Dict[Path, BinwalkResult]:
        """
        Analyze multiple files concurrently.
        
        Args:
            file_paths: List of files to analyze
            extract: Whether to extract identified files
            max_concurrent: Maximum concurrent analyses
        
        Returns:
            Dictionary mapping file paths to results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(file_path: Path) -> tuple[Path, BinwalkResult]:
            async with semaphore:
                result = await self.analyze_file(file_path, extract=extract)
                return file_path, result
        
        tasks = [analyze_with_semaphore(fp) for fp in file_paths]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for item in results_list:
            if isinstance(item, Exception):
                logger.error("Binwalk batch analysis failed: %s", item)
            else:
                file_path, result = item
                results[file_path] = result
        
        return results


class ExiftoolAnalyzer:
    """
    Extract metadata from files using exiftool.
    
    Supports: PE files, Office documents, PDFs, images, archives, etc.
    """
    
    def __init__(self):
        """Initialize exiftool analyzer."""
        if not settings.EXIFTOOL_ENABLED:
            logger.warning("Exiftool is disabled in configuration")
        
        self._verify_installation()
    
    def _verify_installation(self) -> None:
        """Verify exiftool is installed and accessible."""
        try:
            result = subprocess.run(
                [settings.EXIFTOOL_PATH, "-ver"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"Exiftool check failed: {result.stderr}")
            version = result.stdout.strip()
            logger.info("Exiftool verified (version %s) at: %s", version, settings.EXIFTOOL_PATH)
        except FileNotFoundError:
            raise RuntimeError(
                f"Exiftool not found at {settings.EXIFTOOL_PATH}. "
                "Install with: apt-get install libimage-exiftool-perl"
            )
    
    async def extract_metadata(
        self,
        file_path: Path,
        timeout_seconds: int = 60
    ) -> ExiftoolResult:
        """
        Extract metadata from a file.
        
        Args:
            file_path: Path to the file
            timeout_seconds: Maximum execution time
        
        Returns:
            ExiftoolResult with extracted metadata
        """
        if not settings.EXIFTOOL_ENABLED:
            return ExiftoolResult(
                file_path=file_path,
                analyzed_at=datetime.utcnow(),
                success=False,
                metadata={},
                file_type=None,
                error_message="Exiftool is disabled",
                execution_time_seconds=0.0
            )
        
        started_at = datetime.utcnow()
        
        # Build command with JSON output
        cmd = [
            settings.EXIFTOOL_PATH,
            "-json",
            "-g",  # Group output by category
            "-a",  # Extract all tags
            "-s",  # Short tag names
            str(file_path)
        ]
        
        logger.info("Extracting metadata from %s", file_path.name)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
            
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Parse JSON output
            metadata = {}
            file_type = None
            
            if process.returncode == 0:
                try:
                    json_data = json.loads(stdout.decode('utf-8', errors='replace'))
                    
                    # Exiftool returns an array with one element per file
                    if json_data and len(json_data) > 0:
                        metadata = json_data[0]
                        file_type = metadata.get('FileType') or metadata.get('MIMEType')
                
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse exiftool JSON: %s", e)
                    metadata = {}
            
            return ExiftoolResult(
                file_path=file_path,
                analyzed_at=completed_at,
                success=process.returncode == 0,
                metadata=metadata,
                file_type=file_type,
                error_message=None if process.returncode == 0 else stderr.decode('utf-8')[:500],
                execution_time_seconds=execution_time
            )
        
        except asyncio.TimeoutError:
            logger.error("Exiftool analysis timed out for %s", file_path)
            return ExiftoolResult(
                file_path=file_path,
                analyzed_at=datetime.utcnow(),
                success=False,
                metadata={},
                file_type=None,
                error_message=f"Analysis timed out after {timeout_seconds}s",
                execution_time_seconds=timeout_seconds
            )
        
        except Exception as e:
            logger.exception("Exiftool analysis failed for %s", file_path)
            return ExiftoolResult(
                file_path=file_path,
                analyzed_at=datetime.utcnow(),
                success=False,
                metadata={},
                file_type=None,
                error_message=str(e),
                execution_time_seconds=(datetime.utcnow() - started_at).total_seconds()
            )
    
    async def extract_metadata_batch(
        self,
        file_paths: List[Path],
        max_concurrent: int = 4
    ) -> Dict[Path, ExiftoolResult]:
        """
        Extract metadata from multiple files concurrently.
        
        Args:
            file_paths: List of files to process
            max_concurrent: Maximum concurrent extractions
        
        Returns:
            Dictionary mapping file paths to results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(file_path: Path) -> tuple[Path, ExiftoolResult]:
            async with semaphore:
                result = await self.extract_metadata(file_path)
                return file_path, result
        
        tasks = [extract_with_semaphore(fp) for fp in file_paths]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for item in results_list:
            if isinstance(item, Exception):
                logger.error("Exiftool batch extraction failed: %s", item)
            else:
                file_path, result = item
                results[file_path] = result
        
        return results


class ArtifactProcessor:
    """
    Unified artifact post-processing coordinator.
    
    Orchestrates binwalk and exiftool analysis on extracted artifacts.
    """
    
    def __init__(self, extraction_base_dir: Path):
        """
        Initialize the processor.
        
        Args:
            extraction_base_dir: Base directory for extractions
        """
        self.binwalk = BinwalkAnalyzer(extraction_base_dir / "binwalk")
        self.exiftool = ExiftoolAnalyzer()
    
    async def process_artifact(
        self,
        file_path: Path,
        run_binwalk: bool = True,
        run_exiftool: bool = True
    ) -> Dict[str, Any]:
        """
        Process an artifact with all available tools.
        
        Args:
            file_path: Path to the artifact
            run_binwalk: Whether to run binwalk
            run_exiftool: Whether to run exiftool
        
        Returns:
            Normalized processing results
        """
        results = {
            'file_path': str(file_path),
            'file_size_bytes': file_path.stat().st_size if file_path.exists() else 0,
            'processed_at': datetime.utcnow().isoformat(),
            'binwalk': None,
            'exiftool': None
        }
        
        tasks = []
        
        if run_binwalk and settings.BINWALK_ENABLED:
            tasks.append(('binwalk', self.binwalk.analyze_file(file_path)))
        
        if run_exiftool and settings.EXIFTOOL_ENABLED:
            tasks.append(('exiftool', self.exiftool.extract_metadata(file_path)))
        
        # Execute concurrently
        completed_tasks = await asyncio.gather(
            *[task[1] for task in tasks],
            return_exceptions=True
        )
        
        # Map results
        for (name, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                logger.error("%s processing failed: %s", name, result)
                results[name] = {'error': str(result)}
            else:
                results[name] = self._normalize_result(result)
        
        return results
    
    def _normalize_result(self, result) -> Dict[str, Any]:
        """Normalize BinwalkResult or ExiftoolResult to dict."""
        if isinstance(result, BinwalkResult):
            return {
                'success': result.success,
                'signatures_found': result.signatures_found,
                'extracted_file_count': len(result.extracted_files),
                'extracted_files': [str(f) for f in result.extracted_files],
                'error': result.error_message,
                'execution_time_seconds': result.execution_time_seconds
            }
        elif isinstance(result, ExiftoolResult):
            return {
                'success': result.success,
                'file_type': result.file_type,
                'metadata': result.metadata,
                'error': result.error_message,
                'execution_time_seconds': result.execution_time_seconds
            }
        else:
            return {}
