# Project Instructions

- Resolve the non-uv-managed system interpreter with `uv python find --system
  --no-managed-python --no-python-downloads --resolve-links 3.14`.
- Use that returned Python 3.14 path as uv's base interpreter for dependency
  sync and every project Python command; run tests and tools through
  `uv run --python <resolved-path>`. Do not use another Python version.
- Run the Nuitka builder with the `build` dependency group:
  `uv run --python <resolved-path> --group build python tools/build_nuitka.py`.
- Use git to track changes, including submodules. Auto commit msg and push.
- Make sure all tests passed before push.
- Do not send optional commentary.
- Keep every change minimal: touch the fewest files and lines needed, add no
  speculative configurability or abstractions, and do not refactor surrounding
  code. This applies to all current and future modifications.
