# Bootstrap Styling

All styling uses Bootstrap utility classes via `className`. No inline CSS.

## Rules

- Use `className` with Bootstrap classes — never `style={}`
- If a Bootstrap class does not exist for a needed style (e.g., specific pixel heights
  for charts), `style={}` is acceptable with a comment explaining why:
  ```python
  # Bootstrap has no utility for exact chart height
  style={"height": f"{IMPORTANCE_SINGLE_DAY_HEIGHT}px"},
  ```
- Use `className` — never the Python-style `class_name`
- Prefer `dbc` components over raw `html` components when both can achieve the same
  result (e.g., `dbc.Label` over `html.Label`)

## Common Patterns

### Flex layouts

```python
# Vertical stack filling available space
className="d-flex flex-column flex-grow-1"

# Centered content
className="d-flex justify-content-center align-items-center"

# Grow to fill parent
className="flex-grow-1"
```

### Visibility toggling

Toggle visibility by swapping classes in callbacks:

```python
VISIBLE = "d-flex flex-grow-1"
HIDDEN = "d-none"

# In callback:
if show_map:
    return VISIBLE, HIDDEN
return HIDDEN, VISIBLE
```

Define class constants at module level when used in callbacks.

### Responsive columns

```python
# Standard content column (responsive breakpoints)
className="col-md-11 col-lg-10 col-xl-9"

# Centered inner content
className="col-11 col-xl-8 mx-auto"
```

### Spacing

```python
# Margins: m-{1-5}, mt-, mb-, ms-, me-, mx-, my-
# Padding: p-{1-5}, pt-, pb-, ps-, pe-, px-, py-
className="m-2 mb-4 p-0"
```

### Text

```python
className="text-center"        # alignment
className="text-muted"         # secondary text
className="fw-bold"            # bold (not style={"font-weight": "bold"})
className="font-monospace"     # monospace
className="fs-4"               # font size
```

### Dynamic class changes

Use `swap_classes()` to replace a class prefix:

```python
from cosmopolitan_app.utils import swap_classes

# Replaces any existing bg-* class with bg-info
new_class = swap_classes("bg-info", current_class_name)
```

## Justified Exceptions

When `style={}` is necessary (no Bootstrap class exists), add an inline comment:

```python
# no Bootstrap class for white-space: pre-wrap
style={"white-space": "pre-wrap"},
```

Every `style={}` in the codebase must either be replaced with a Bootstrap class or
have a comment explaining why it can't be.
