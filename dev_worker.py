#!/usr/bin/env python3
"""Development Celery worker with auto-reload on code changes."""

import subprocess
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

celery_command = [
    "celery",
    "-A",
    "cosmopolitan_app.background_job_manager.celery",
    "worker",
    "--loglevel=debug",  # Keep debug level but filter noisy loggers
    "--concurrency=2",
    "--queues=default,computation,maintenance",
    "--hostname=worker@dev",
    "--pool=solo",
    "-E",  # Enable task events for inspect API
]


class CeleryRestartHandler(FileSystemEventHandler):
    """Handler to restart Celery worker on Python file changes."""

    def __init__(self, worker_process=None):
        """Initialize the handler."""
        self.worker_process = worker_process
        self.restart_scheduled = False

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Only restart on Python file changes
        if event.src_path.endswith(".py"):
            print(f"Code change detected: {event.src_path}")
            self.schedule_restart()

    def schedule_restart(self):
        """Schedule a restart (debounced)."""
        if self.restart_scheduled:
            return

        self.restart_scheduled = True
        time.sleep(1)  # Debounce multiple rapid changes
        self.restart_worker()
        self.restart_scheduled = False

    def restart_worker(self):
        """Restart the Celery worker process."""
        print("Restarting Celery worker...")

        if self.worker_process and self.worker_process.poll() is None:
            self.worker_process.terminate()
            self.worker_process.wait()

        # Start new worker process
        self.worker_process = subprocess.Popen(celery_command)

        print(f"Celery worker restarted with PID: {self.worker_process.pid}")


def main():
    """Run Celery worker with auto-reload."""
    print("Starting Celery worker in development mode with auto-reload...")

    # Initial worker start
    worker_process = subprocess.Popen(celery_command)

    # Set up file watcher
    event_handler = CeleryRestartHandler(worker_process)
    observer = Observer()

    # Watch the cosmopolitan_app directory
    watch_path = Path(__file__).parent / "cosmopolitan_app"
    observer.schedule(event_handler, str(watch_path), recursive=True)

    print(f"Watching for changes in: {watch_path}")
    observer.start()

    try:
        while True:
            time.sleep(1)
            # Check if worker process died
            if worker_process.poll() is not None:
                print("Worker process died, restarting...")
                event_handler.restart_worker()
                worker_process = event_handler.worker_process

    except KeyboardInterrupt:
        print("Shutting down...")
        observer.stop()
        if worker_process and worker_process.poll() is None:
            worker_process.terminate()
            worker_process.wait()

    observer.join()


if __name__ == "__main__":
    main()
