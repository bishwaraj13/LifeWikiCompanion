import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import default_data_root, resolve_data_root


class ConfigTests(unittest.TestCase):
    def test_default_data_root_is_outside_code_repo_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            root = default_data_root(home=Path("/home/example"), platform="linux")

        self.assertEqual(root, Path("/home/example/.local/share/lifewiki-companion"))

    def test_env_var_overrides_default_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LIFEWIKI_DATA_DIR": tmp}):
                self.assertEqual(resolve_data_root(None), Path(tmp).resolve())

    def test_cli_data_root_wins_over_env_var(self):
        with tempfile.TemporaryDirectory() as tmp:
            explicit = Path(tmp) / "explicit"
            with patch.dict(os.environ, {"LIFEWIKI_DATA_DIR": str(Path(tmp) / "env")}):
                self.assertEqual(resolve_data_root(str(explicit)), explicit.resolve())


if __name__ == "__main__":
    unittest.main()
