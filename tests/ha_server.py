#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import signal
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_HA_CONFIG_DIR = _REPO_ROOT / "tests" / "ha-config"
_HA_VERSION_FILE = _REPO_ROOT / "tests" / "HA_VERSION"
_DIST_JS = _REPO_ROOT / "dist" / "slider-entity-row.js"
_ENV_FILE = _REPO_ROOT / ".ha_env"


def _default_ha_version() -> str:
    if not _HA_VERSION_FILE.exists():
        print(f"{_HA_VERSION_FILE} is missing.", file=sys.stderr)
        sys.exit(1)
    ha_version = _HA_VERSION_FILE.read_text(encoding="utf-8").strip()
    if not ha_version:
        print(f"{_HA_VERSION_FILE} is empty.", file=sys.stderr)
        sys.exit(1)
    return ha_version


def main() -> None:
    try:
        from ha_testcontainer import HATestContainer
    except ImportError:
        print("ha_testcontainer is not installed. Run: pip install -e '.[test]'", file=sys.stderr)
        sys.exit(1)

    if not _DIST_JS.exists():
        print("dist/slider-entity-row.js is missing. Run: npm run build", file=sys.stderr)
        sys.exit(1)

    ha_version = os.environ.get("HA_VERSION") or _default_ha_version()
    ha_tmp = Path(tempfile.mkdtemp(prefix="slider-row-ha-state-"))
    shutil.copytree(str(_HA_CONFIG_DIR), str(ha_tmp), dirs_exist_ok=True)

    container = HATestContainer(version=ha_version, config_path=ha_tmp)
    container.with_volume_mapping(str(_REPO_ROOT.resolve()), "/config/www/workspace", "rw")
    container.start()

    url = container.get_url()
    token = container.get_token()
    _ENV_FILE.write_text(f"export HA_URL={url}\nexport HA_TOKEN={token}\n")

    print(f"export HA_URL={url}")
    print(f"export HA_TOKEN={token}")

    def _shutdown(_sig: int, _frame: object) -> None:
        try:
            container.stop()
        finally:
            _ENV_FILE.unlink(missing_ok=True)
            shutil.rmtree(ha_tmp, ignore_errors=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.pause()


if __name__ == "__main__":
    main()