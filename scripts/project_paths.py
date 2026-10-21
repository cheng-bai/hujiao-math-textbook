"""Portable project entrypoints; no Codex or machine-specific paths required."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def portable_record(value):
    """Store project-local paths without binding build records to this checkout."""
    if isinstance(value, dict):
        return {portable_record(k): portable_record(v) for k, v in value.items()}
    if isinstance(value, list):
        return [portable_record(v) for v in value]
    if isinstance(value, str):
        prefixes = {str(ROOT) + os.sep, str(ROOT) + '\\', ROOT.as_posix() + '/'}
        for prefix in prefixes:
            if value.startswith(prefix) and '\n' not in value:
                return value[len(prefix):].replace('\\', '/')
        for prefix in prefixes:
            value = value.replace(prefix, '')
        return value
    return value


def use_project_root():
    """Legacy source records are relative to the repository, not the caller's cwd."""
    os.chdir(ROOT)


def launch_browser(playwright, **options):
    """Prefer Playwright Chromium; allow an explicit installed Chrome override."""
    channel = os.environ.get('HUJIAO_BROWSER_CHANNEL')
    if channel:
        return playwright.chromium.launch(channel=channel, **options)
    try:
        # The full Chromium binary can exist while its headless shell is absent.
        return playwright.chromium.launch(**options)
    except Exception as primary:
        try:
            return playwright.chromium.launch(channel='chrome', **options)
        except Exception:
            raise RuntimeError(
                'Install a test browser with: python -m playwright install chromium; '
                'or set HUJIAO_BROWSER_CHANNEL=chrome for installed Chrome.'
            ) from primary
