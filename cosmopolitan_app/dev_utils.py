"""Development utilities for the Cosmopolitan app."""

import dash_bootstrap_components as dbc


def list_all_component_ids(layout):
    """Recursively extract all component IDs from a Dash layout."""
    component_ids = []

    # Handle if layout is a list (like in your case)
    if isinstance(layout, list):
        for item in layout:
            if item is not None:
                component_ids.extend(list_all_component_ids(item))
        return component_ids

    # Skip if layout is None or not a valid component
    if layout is None or isinstance(layout, (str, int, float, bool)):
        return component_ids

    # Check for id attribute directly (for components like dbc.Input)
    if hasattr(layout, "id") and layout.id is not None:
        component_ids.append(layout.id)

    # Check for component_id (for some Dash components)
    if hasattr(layout, "component_id") and layout.component_id is not None:
        component_ids.append(layout.component_id)

    # Process children if any
    if hasattr(layout, "children"):
        children = layout.children
        if children is not None:
            if isinstance(children, list):
                for child in children:
                    if child is not None:
                        component_ids.extend(list_all_component_ids(child))
            else:
                component_ids.extend(list_all_component_ids(children))

    return component_ids


# Alternative approach that should catch more components
def extract_all_ids(layout):
    """Extract all IDs from any dash component or container."""
    ids = []

    # If it's a list, process each item
    if isinstance(layout, list):
        for item in layout:
            ids.extend(extract_all_ids(item))
        return ids

    # If it's not a dash component, return empty list
    if layout is None or isinstance(layout, (str, int, float, bool)):
        return ids

    # Check for id attribute - works with most Dash components
    if hasattr(layout, "id") and layout.id is not None:
        ids.append(layout.id)

    # Process children if available
    if hasattr(layout, "children"):
        children = layout.children
        if children is not None:
            if isinstance(children, list):
                for child in children:
                    ids.extend(extract_all_ids(child))
            else:
                ids.extend(extract_all_ids(children))

    # Navigate through properties that might contain components
    # This helps with dashboard components that organize other components
    for key in dir(layout):
        if (
            not key.startswith("_")
            and key not in ["children", "id", "style", "className"]
            and not callable(getattr(layout, key, None))
        ):
            value = getattr(layout, key)
            # Only recurse if it looks like it might be a component
            if (
                hasattr(value, "id")
                or hasattr(value, "children")
                or isinstance(value, (list, dict))
            ):
                ids.extend(extract_all_ids(value))

    return ids


# Check for callbacks referencing a specific component ID
def find_callbacks_with_component(app, component_id):
    """Find callbacks that reference a specific component ID."""
    results = []

    if not hasattr(app, "callback_map"):
        return results

    for callback_id, callback_spec in app.callback_map.items():
        found = False
        location = None

        # Check inputs
        if "inputs" in callback_spec:
            for input_item in callback_spec["inputs"]:
                if (
                    hasattr(input_item, "component_id")
                    and input_item.component_id == component_id
                ):
                    found = True
                    location = "inputs"
                    break

        # Check states
        if not found and "state" in callback_spec:
            for state_item in callback_spec["state"]:
                if (
                    hasattr(state_item, "component_id")
                    and state_item.component_id == component_id
                ):
                    found = True
                    location = "state"
                    break

        # Check outputs
        if not found and "outputs" in callback_spec:
            for output_item in callback_spec["outputs"]:
                if (
                    hasattr(output_item, "component_id")
                    and output_item.component_id == component_id
                ):
                    found = True
                    location = "outputs"
                    break

        if found:
            results.append(
                {
                    "callback_id": callback_id,
                    "location": location,
                    "spec": callback_spec,
                }
            )

    return results


if __name__ == "__main__":
    layout = dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Label("Email"),
                    dbc.Input(
                        id="email",
                        type="email",
                        value="test@test.com",
                        disabled=True,
                        size="sm",
                        style={"width": "auto", "background-color": "#e9ecef"},
                    ),
                    dbc.FormText(
                        "Email address to be notified when job submission is complete."
                    ),
                    dbc.FormFeedback(id="email_feedback"),
                ]
            )
        ]
    )
    all_ids = list_all_component_ids(layout)
    print("All component IDs:", all_ids)
