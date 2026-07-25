# Project Instructions

- `.python-version` pins this project to Python 3.14.
- Resolve the non-uv-managed system interpreter with `uv python find --system
  --no-managed-python --no-python-downloads --resolve-links 3.14`.
- Use that returned Python 3.14 path as uv's base interpreter for dependency
  sync and every project Python command; run tests and tools through
  `uv run --python <resolved-path>`. Do not use another Python version.
- Use git to track changes. Auto commit msg and push.
- Do not send optional commentary.
