"""Utility functions for the web service."""

import re
import time


def swap_classes(new_class: str, class_name: str) -> str:
    """Replace or add a class with the same prefix as new_class in a className string.

    The prefix is automatically extracted from the new_class.

    Parameters:
    new_class (str): The new class to add (e.g., "bg-primary", "text-white")
    class_name (str): The original className string

    Returns:
    str: The updated className string with the replaced class

    Examples:
    >>> swap_classes("bg-primary", "bg-info rounded-top py-2 mb-4")
    'bg-primary rounded-top py-2 mb-4'
    >>> swap_classes("text-danger", "bg-info text-dark py-2")
    'bg-info text-danger py-2'
    """
    # Extract prefix from new_class
    prefix_match = re.match(r"^([a-zA-Z0-9]+)-", new_class)
    if not prefix_match:
        raise ValueError(
            f"New class '{new_class}' must have a prefix followed by a hyphen (e.g., 'bg-primary')"  # noqa
        )

    class_prefix = prefix_match.group(1)

    # Pattern to match classes with the given prefix
    class_pattern = rf"\b{class_prefix}-[a-zA-Z0-9]+"

    # Check if a class with the given prefix exists
    match = re.search(class_pattern, class_name)

    if match:
        # Replace existing class with the new one
        updated_class_name = re.sub(class_pattern, new_class, class_name)
        return updated_class_name
    else:
        # Add new class if none with the prefix exists
        return f"{class_name} {new_class}"


def wait_for_all_images_loaded(driver, timeout=5):
    """Wait for all images on the page to be loaded.

    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum time to wait in seconds (default: 5)

    Returns:
        bool: True if all images loaded within timeout, False otherwise
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        all_loaded = driver.execute_script(
            """
            return Array.from(document.images).every(img => img.complete);
        """
        )
        if all_loaded:
            return True
        time.sleep(0.1)
    return False
