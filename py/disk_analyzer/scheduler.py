"""Scheduler for periodic disk analysis."""

import time
import logging
import signal
import sys
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """Simple scheduler for running tasks at intervals."""
    
    def __init__(self, interval_seconds: int):
        self.interval = interval_seconds
        self.running = False
        self._setup_signal_handlers()
        
        logger.info(f"Scheduler initialized with interval: {interval_seconds}s")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def start(self, task: Callable, *args, **kwargs):
        """Start the scheduler loop."""
        self.running = True
        iteration = 0
        
        logger.info("Scheduler started")
        
        while self.running:
            iteration += 1
            logger.info(f"Running task (iteration {iteration})")
            
            try:
                task(*args, **kwargs)
            except Exception as e:
                logger.error(f"Task execution failed: {e}", exc_info=True)
            
            if self.running:
                logger.debug(f"Sleeping for {self.interval}s")
                time.sleep(self.interval)
        
        logger.info("Scheduler stopped")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False


def run_scheduled(
    interval: int,
    task: Callable,
    max_iterations: Optional[int] = None,
    *args,
    **kwargs
):
    """Run a task at scheduled intervals."""
    scheduler = Scheduler(interval)
    
    if max_iterations:
        for i in range(max_iterations):
            if not scheduler.running:
                break
            logger.info(f"Running task (iteration {i + 1}/{max_iterations})")
            try:
                task(*args, **kwargs)
            except Exception as e:
                logger.error(f"Task execution failed: {e}", exc_info=True)
            if i < max_iterations - 1:
                time.sleep(interval)
    else:
        scheduler.start(task, *args, **kwargs)
