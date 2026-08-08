# Project Instructions

- Resolve the non-uv-managed system interpreter with `uv python find --system
  --no-managed-python --no-python-downloads --resolve-links 3.14`.
- Use that returned Python 3.14 path as uv's base interpreter for dependency
  sync and every project Python command; run tests and tools through
  `uv run --python <resolved-path>`. Do not use another Python version.
- Run the Nuitka builder with the `build` dependency group:
  `uv run --python <resolved-path> --group build python tools/build_nuitka.py`.
- Use git to track changes, including submodules. Auto commit msg and push.
- Run `uv sync --python <resolved-path> --extra dev --reinstall-package
  PyProxySwitch` before running local tests; a plain sync does not refresh the
  editable install's version metadata and leaves the versioning tests failing.
- Before pushing, pass every check in RELEASING.md's "按需高级操作参考 →
  单独运行检查" section. When `pyproxyswitch/gui/*.py` or
  `pyproxyswitch/resources/*.ui` change, regenerate with `tools/generate_ui.py`
  and `tools/generate_i18n.py` in the SAME commit — lupdate records source
  line numbers in `i18n/*.ts`, so any line shift otherwise fails CI's
  `generate_i18n.py --check` with "Out of date".
- Make sure all tests and checks in `RELEASING.md` pass before pushing.
- Do not send optional commentary.
- Keep every change minimal: touch the fewest files and lines needed, add no
  speculative configurability or abstractions, and do not refactor surrounding
  code. This applies to all current and future modifications.
