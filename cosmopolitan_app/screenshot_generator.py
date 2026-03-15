"""Screenshot generator for documentation pages.

This module automates screenshot capture for all documentation pages using Selenium.
"""

import logging
import time
import urllib.request
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from cosmopolitan_app.utils import wait_for_all_images_loaded

log = logging.getLogger(__name__)

# Pages to screenshot (module_name, url_path, display_title)
PAGES_TO_SCREENSHOT = [
    # User workflow (5 pages)
    (1, "home", "/", "Home Page"),
    (3, "new_job", "/new-job", "Create New Job"),
    (3, "input", "/input/{job_id_new}", "Job Input Form"),
    (3, "submission", "/submission/{job_id_finished}", "Job Submission"),
    (3, "results", "/results/{job_id_finished}", "View Results"),
    # Admin pages (6 pages)
    (1, "job_management", "/job-management", "Job Management"),
    (3, "sensor_management", "/sensor_management", "Sensor Management"),
    (1, "measurment_view", "/measurment-view", "Measurement Database"),
    (1, "crns_db_admin", "/crns-admin", "CRNS Database Administration"),
    (1, "logs", "/logs", "Application Logs"),
    (1, "worker_management", "/worker_management", "Worker Management"),
]


class ScreenshotGenerator:
    """Automate screenshot capture for documentation pages."""

    def __init__(
        self,
        job_id_finished: str,
        job_id_new: str,
        headless: bool = True,
        viewport_size: tuple = (1920, 1080),
    ) -> None:
        """Initialize screenshot generator.

        Args:
            headless: Run browser in headless mode (default: True)
            viewport_size: Browser viewport dimensions (default: 1920x1080)
        """
        self.headless = headless
        self.viewport_size = viewport_size
        self.driver = None
        self.base_url = "http://localhost:8080"  # Assumes dev_up.sh mock is running
        self.job_id_finished = job_id_finished
        self.job_id_new = job_id_new

    def setup_driver(self) -> webdriver.Chrome:
        """Configure and return Chrome WebDriver.

        Returns:
            Configured Chrome WebDriver instance
        """
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            f"--window-size={self.viewport_size[0]},{self.viewport_size[1]}"
        )

        driver = webdriver.Chrome(options=options)
        driver.set_window_size(self.viewport_size[0], self.viewport_size[1])

        log.info(
            f"WebDriver initialized (headless={self.headless}, viewport={self.viewport_size})",  # noqa
        )

        return driver

    def wait_for_page_ready(self, timeout: int = 10) -> bool:
        """Wait for page to be fully loaded.

        Waits for images to load AND Dash callbacks to complete. This includes
        waiting for external data sources like TimeIO sensor management.

        Args:
            timeout: Maximum time to wait in seconds (default: 10)

        Returns:
            True if page ready within timeout, False otherwise
        """
        end_time = time.time() + timeout

        while time.time() < end_time:
            # Check if Dash is updating
            is_updating = self.driver.execute_script(
                "return document.querySelector('._dash-updating') !== null;"
            )

            if not is_updating:
                # Wait for images to load
                if wait_for_all_images_loaded(self.driver, timeout=5):
                    return True

            time.sleep(0.1)

        return False

    def capture_screenshot(
        self, page_name: str, page_url: str, output_dir: Path, init_wait_time: int
    ) -> None:
        """Navigate to page and capture screenshot.

        Args:
            page_name: Module name for filename (e.g., 'home')
            page_url: URL path to navigate to (e.g., '/')
            output_dir: Directory to save screenshot

        Raises:
            Any exception from navigation or screenshot capture
        """
        url = f"{self.base_url}{page_url}"
        output_path = output_dir / f"{page_name}.png"

        log.info(
            f"Capturing screenshot: {page_name} from {url}",
        )

        # Navigate to page
        self.driver.get(url)
        time.sleep(init_wait_time)

        # Wait for page to be ready
        self.wait_for_page_ready(timeout=10)

        # Capture screenshot
        self.driver.save_screenshot(str(output_path))

        log.info(f"Screenshot saved: {output_path}")

    def generate_all_screenshots(self, output_dir: Path) -> None:
        """Capture screenshots for all documentation pages.

        Assumes Flask app server is already running at self.base_url.

        Args:
            output_dir: Directory to save screenshots

        Raises:
            Any exception from screenshot capture (fail-fast approach)
        """
        log.info(
            f"Starting screenshot generation to {output_dir}",
        )

        # Setup WebDriver
        self.driver = self.setup_driver()

        # Verify server is accessible
        log.info(f"Checking server at {self.base_url}...")
        urllib.request.urlopen(self.base_url, timeout=5)
        log.info(f"Server accessible at {self.base_url}")

        # Capture all screenshots (no try/except - fail fast)
        for init_wait_time, page_name, page_url, page_title in PAGES_TO_SCREENSHOT:
            if "{job_id_finished}" in page_url:
                page_url = page_url.format(job_id_finished=self.job_id_finished)
            if "{job_id_new}" in page_url:
                page_url = page_url.format(job_id_new=self.job_id_new)
            self.capture_screenshot(page_name, page_url, output_dir, init_wait_time)

        log.info(
            f"All {len(PAGES_TO_SCREENSHOT)} screenshots captured successfully",
        )

    def cleanup(self):
        """Clean up WebDriver."""
        if self.driver:
            self.driver.quit()
            log.info("WebDriver closed")
