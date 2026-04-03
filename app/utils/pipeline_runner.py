"""
Pipeline runner utility.
Runs SpecWatch pipelines in background threads from Flask UI.
Runs pipelines in separate threads to avoid blocking Flask.
Tracks pipeline status for UI progress updates.
"""

import subprocess
import threading
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


# Background pipeline runner for Flask app. Runs pipelines in separate threads to avoid blocking Flask.
# Using sys.executable for cross platform compatibility.
class PipelineRunner:
    
    # Initialize pipeline runner
    def __init__(self):

        self.status = {
            "running": False,
            "current_stage": None,
            "progress": 0,
            "message": "",
            "result": None,
            "started_at": None,
            "completed_at": None,
            "logs": []
        }
        self.current_thread: Optional[threading.Thread] = None
        
        # Use the same Python interpreter that's running Flask
        self.python_cmd = sys.executable
        logger.info(f"PipelineRunner initialized with Python: {self.python_cmd}")
    
    # Check if a pipeline is currently running
    def is_running(self) -> bool:
        return self.status["running"]
    
    # Get current pipeline status
    def get_status(self) -> Dict[str, Any]:
        return self.status.copy()
    
    # Run discovery pipeline in background
    def run_discovery(self):

        if self.is_running():
            raise RuntimeError("Pipeline already running")
        
        stages = ["Discovery"]
        command = [self.python_cmd, "-m", "pipelines.discovery_pipeline"]
        
        self._run_pipeline_thread(command, stages, "discovery")
    
    # Run analysis pipeline (ingestion → classification) in background
    def run_analysis(self):

        if self.is_running():
            raise RuntimeError("Pipeline already running")
        
        self._run_analysis_sequence()
    
    # Run full pipeline (all stages) in background
    def run_full_pipeline(self):

        if self.is_running():
            raise RuntimeError("Pipeline already running")
        
        self._run_full_sequence()
    
    # Run alerting pipeline in background
    def run_alerting(self):

        if self.is_running():
            raise RuntimeError("Pipeline already running")
        
        command = [self.python_cmd, "-m", "pipelines.alerting_pipeline"]
        stages = ["Alerting"]
        
        self._run_pipeline_thread(command, stages, "alerting")
    
    # Run all analysis pipelines in sequence
    def _run_analysis_sequence(self):

        def run():
            self._update_status(running=True, progress=0, message="Starting analysis...")
            
            try:
                # Ingestion (20%)
                self._update_status(current_stage="Ingestion", progress=20, message="Fetching API specs...")
                self._run_subprocess([self.python_cmd, "-m", "pipelines.ingestion_pipeline"], "Ingestion")
                
                # Normalization (40%)
                self._update_status(current_stage="Normalization", progress=40, message="Normalizing schemas...")
                self._run_subprocess([self.python_cmd, "-m", "pipelines.normalization_pipeline"], "Normalization")
                
                # Diff (60%)
                self._update_status(current_stage="Diff", progress=60, message="Detecting changes...")
                self._run_subprocess([self.python_cmd, "-m", "pipelines.diff_pipeline"], "Diff")
                
                # Classification (80%)
                self._update_status(current_stage="Classification", progress=80, message="Analyzing with LLM...")
                self._run_subprocess([self.python_cmd, "-m", "pipelines.classification_pipeline"], "Classification")
                
                # Complete
                self._update_status(
                    current_stage="Complete",
                    progress=100,
                    message="Analysis pipeline completed successfully!",
                    result="success"
                )
                logger.info("Analysis pipeline sequence completed successfully")
            
            except Exception as e:
                logger.error(f"Analysis pipeline error: {str(e)}")
                self._update_status(
                    result="error",
                    message=f"Pipeline failed: {str(e)}"
                )
            
            finally:
                self.status["running"] = False
                self.status["completed_at"] = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')
        
        self.current_thread = threading.Thread(target=run, daemon=True)
        self.current_thread.start()
    
    # Run full pipeline via main.py
    def _run_full_sequence(self):

        def run():
            self._update_status(running=True, progress=0, message="Starting full pipeline...")
            
            try:
                self._update_status(current_stage="Running", progress=10, message="Executing all stages...")
                
                logger.info(f"Executing: {self.python_cmd} main.py")
                logger.info(f"Working directory: {Path.cwd()}")
                
                result = subprocess.run(
                    [self.python_cmd, "main.py"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=Path.cwd()
                )
                
                # Log output
                if result.stdout:
                    logger.info(f"Pipeline stdout (first 1000 chars): {result.stdout[:1000]}")
                if result.stderr:
                    logger.warning(f"Pipeline stderr: {result.stderr}")
                
                if result.returncode != 0:
                    raise Exception(f"Pipeline failed with code {result.returncode}: {result.stderr}")
                
                # Complete
                self._update_status(
                    current_stage="Complete",
                    progress=100,
                    message="Full pipeline completed successfully!",
                    result="success"
                )
                logger.info("Full pipeline completed successfully")
            
            except subprocess.TimeoutExpired:
                self._update_status(
                    result="error",
                    message="Pipeline timed out after 5 minutes"
                )
                logger.error("Full pipeline timed out")
            
            except Exception as e:
                logger.error(f"Full pipeline error: {str(e)}", exc_info=True)
                self._update_status(
                    result="error",
                    message=f"Pipeline failed: {str(e)}"
                )
            
            finally:
                self.status["running"] = False
                self.status["completed_at"] = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')
        
        self.current_thread = threading.Thread(target=run, daemon=True)
        self.current_thread.start()
    
    # Run a subprocess and raise exception on failure
    def _run_subprocess(self, command: list, stage_name: str):

        logger.info(f"Executing {stage_name}: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=Path.cwd()
        )
        
        if result.stdout:
            logger.debug(f"{stage_name} stdout: {result.stdout[:500]}")
        if result.stderr:
            logger.warning(f"{stage_name} stderr: {result.stderr[:500]}")
        
        if result.returncode != 0:
            raise Exception(f"{stage_name} failed with code {result.returncode}: {result.stderr}")
        
        logger.info(f"{stage_name} completed successfully")
    
    # Run pipeline command in background thread
    def _run_pipeline_thread(self, command: list, stages: list, pipeline_name: str):

        def run():
            self._update_status(
                running=True,
                progress=0,
                current_stage=stages[0] if stages else "Running",
                message=f"Starting {pipeline_name} pipeline..."
            )
            
            logger.info(f"Executing {pipeline_name}: {' '.join(command)}")
            logger.info(f"Working directory: {Path.cwd()}")
            
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=Path.cwd()
                )
                
                # Log output for debugging
                if result.stdout:
                    logger.info(f"{pipeline_name} stdout (first 1000 chars): {result.stdout[:1000]}")
                if result.stderr:
                    logger.warning(f"{pipeline_name} stderr: {result.stderr[:1000]}")
                
                logger.info(f"{pipeline_name} subprocess completed with returncode: {result.returncode}")
                
                # Check result
                if result.returncode == 0:
                    self._update_status(
                        progress=100,
                        current_stage="Complete",
                        message=f"{pipeline_name.capitalize()} pipeline completed successfully!",
                        result="success"
                    )
                    logger.info(f"{pipeline_name} pipeline completed successfully")
                else:
                    error_msg = result.stderr or result.stdout or f"Unknown error (code {result.returncode})"
                    self._update_status(
                        result="error",
                        message=f"Pipeline failed: {error_msg[:200]}"
                    )
                    logger.error(f"{pipeline_name} pipeline failed with code {result.returncode}: {error_msg}")
            
            except subprocess.TimeoutExpired:
                self._update_status(
                    result="error",
                    message="Pipeline timed out after 5 minutes"
                )
                logger.error(f"{pipeline_name} pipeline timed out")
            
            except FileNotFoundError as e:
                self._update_status(
                    result="error",
                    message=f"Command not found: {e}"
                )
                logger.error(f"{pipeline_name} - command not found: {e}")
            
            except Exception as e:
                self._update_status(
                    result="error",
                    message=f"Error: {str(e)}"
                )
                logger.error(f"{pipeline_name} pipeline error: {str(e)}", exc_info=True)
            
            finally:
                self.status["running"] = False
                self.status["completed_at"] = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')
        
        self.current_thread = threading.Thread(target=run, daemon=True)
        self.current_thread.start()
    
    # Update pipeline status
    def _update_status(self, **kwargs):

        for key, value in kwargs.items():
            if key in self.status:
                self.status[key] = value
        
        # Add timestamp to logs
        if "message" in kwargs:
            self.status["logs"].append({
                "timestamp": datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S'),
                "message": kwargs["message"]
            })
            logger.info(kwargs["message"])
    
    # Reset pipeline status
    def reset(self):

        if self.status["running"]:
            logger.warning("Forcing pipeline status reset while running")
        
        self.status = {
            "running": False,
            "current_stage": None,
            "progress": 0,
            "message": "",
            "result": None,
            "started_at": None,
            "completed_at": None,
            "logs": []
        }


# Global singleton instance
_runner = None

# Get global pipeline runner instance
def get_pipeline_runner() -> PipelineRunner:

    global _runner
    if _runner is None:
        _runner = PipelineRunner()
    return _runner
