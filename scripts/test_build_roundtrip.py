#!/usr/bin/env python3
"""Rebuild, then reuse a portable cached chapter without touching shipped pages."""
import json
from pathlib import Path
import tempfile
import zipfile

import batch_render


def main():
    root = batch_render.ROOT
    checks = root / 'release-checks'
    checks.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='build-roundtrip-', dir=checks) as folder:
        batch_render.OUTPUT = Path(folder)
        section = root / 'batch/sections/x1/x1-2-3.json'
        fresh = batch_render.render_section(section, force=True)
        cached = batch_render.render_section(section)
        assert fresh['status'] == 'rendered', fresh['issues']
        assert cached['cached'] and Path(cached['output']).is_absolute()
        assert fresh['artifact_hashes'] == cached['artifact_hashes']
        record = Path(cached['output']) / 'build.json'
        saved = json.loads(record.read_text(encoding='utf-8'))
        assert not Path(saved['output']).is_absolute()
        assert str(root) not in record.read_text(encoding='utf-8')
        with zipfile.ZipFile(Path(cached['output']) / 'student.zip') as archive:
            assert archive.testzip() is None
        print('Build roundtrip passed: relative sources, cached output, hashes, student ZIP.')


if __name__ == '__main__':
    main()
