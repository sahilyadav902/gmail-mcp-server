# Publishing `sudo-gmail-mcp` to PyPI

This guide covers:
- publishing the package to PyPI for the first time
- publishing updates when you add new features or fixes

## Prerequisites

Make sure you have:
- Python 3.10+
- a PyPI account
- optionally a TestPyPI account for dry runs
- this repository checked out locally

Useful links:
- PyPI: https://pypi.org/
- TestPyPI: https://test.pypi.org/

## One-time setup

Install the packaging tools:

```bash
python -m pip install --upgrade pip
pip install -e .[dev]
```

This installs:
- `build` for creating source and wheel distributions
- `twine` for validating and uploading distributions

## Files that control the published version

Before every release, check these files:
- `pyproject.toml`
- `src/gmail_mcp/__init__.py`

The version should match in both places.

Example:

```toml
version = "0.1.0"
```

```python
__version__ = "0.1.0"
```

## First-time publish flow

### 1. Run tests

```bash
python -m pytest
```

### 2. Build the package

```bash
python -m build
```

This creates:
- `dist/gmail_mcp-<version>.tar.gz`
- `dist/gmail_mcp-<version>-py3-none-any.whl`

### 3. Validate the package metadata

```bash
python -m twine check dist/*
```

### 4. Upload to TestPyPI first

```bash
python -m twine upload --repository testpypi dist/*
```

You will be prompted for your TestPyPI credentials unless you have them configured already.

### 5. Verify install from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple sudo-gmail-mcp
```

Then test the installed command:

```bash
sudo-gmail-mcp
```

### 6. Upload to real PyPI

```bash
python -m twine upload dist/*
```

### 7. Verify install from PyPI

```bash
pip install sudo-gmail-mcp
```

Run it:

```bash
sudo-gmail-mcp
```

## Releasing a new version after code changes

Whenever you add features, fix bugs, or change package behavior, publish a new version.

### 1. Update the version number

Update both:
- `pyproject.toml`
- `src/gmail_mcp/__init__.py`

Example version bumps:
- bug fix only: `0.1.0` -> `0.1.1`
- new backward-compatible feature: `0.1.0` -> `0.2.0`
- breaking change: `0.1.0` -> `1.0.0`

### 2. Remove old build artifacts

Do this before rebuilding so you do not accidentally upload older files.

```bash
rm -rf dist build src/*.egg-info
```

On Windows PowerShell:

```powershell
Remove-Item -Recurse -Force dist, build
Remove-Item -Recurse -Force src\gmail_mcp.egg-info
```

### 3. Reinstall dev dependencies if needed

```bash
pip install -e .[dev]
```

### 4. Run tests again

```bash
python -m pytest
```

### 5. Build the new release

```bash
python -m build
```

### 6. Validate the release files

```bash
python -m twine check dist/*
```

### 7. Upload the new version

Optional dry run to TestPyPI:

```bash
python -m twine upload --repository testpypi dist/*
```

Real release:

```bash
python -m twine upload dist/*
```

## Important PyPI rule

You cannot upload a second package with the same version number.

If `0.1.0` is already published and you changed the code, you must bump the version before uploading again.

## Recommended release workflow

For every release:

1. finish code changes
2. update version in both files
3. run tests
4. clear old build artifacts
5. build package
6. run `twine check`
7. upload to TestPyPI if desired
8. upload to PyPI
9. verify `pip install sudo-gmail-mcp`
10. optionally create a matching git tag

## Optional git tagging

After publishing, you may want to create a release tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

For a later release:

```bash
git tag v0.1.1
git push origin v0.1.1
```

## Quick command summary

### First release

```bash
pip install -e .[dev]
python -m pytest
python -m build
python -m twine check dist/*
python -m twine upload --repository testpypi dist/*
python -m twine upload dist/*
```

### New release

```bash
# bump version in pyproject.toml and src/gmail_mcp/__init__.py
rm -rf dist build src/*.egg-info
pip install -e .[dev]
python -m pytest
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

## Notes

- Keep `credentials.json` and token files out of the package and repository.
- Make sure the README stays accurate because it becomes the PyPI project description.
- Test the installed CLI after every release, not just editable installs.
