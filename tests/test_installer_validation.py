# -*- coding: utf-8 -*-
"""Installer syntax validation tests, without an Enigma2 receiver."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class InstallerValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        installer = (ROOT / 'installer.sh').read_text(encoding='utf-8')
        start = installer.index('validate_python_tree() {')
        end = installer.index('\n}\n\n# ===== Parsowanie argumentów =====', start)
        cls.function = installer[start:end + 2]
        # Verify neither pre- nor post-install check still depends on compileall.
        cls.installer = installer

    def run_validator(self, source):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / 'src'
            (source_dir / 'nested').mkdir(parents=True)
            (source_dir / 'nested' / 'main.py').write_bytes(source)
            fake_stdlib = root / 'fake_stdlib'
            fake_stdlib.mkdir()
            (fake_stdlib / 'py_compile.py').write_text(
                'raise ModuleNotFoundError("No module named py_compile")\n',
                encoding='utf-8',
            )
            env = dict(os.environ)
            env['PYTHONPATH'] = str(fake_stdlib)
            return subprocess.run(
                ['sh', '-c', self.function + '\nvalidate_python_tree "$1"\n',
                 'sh', str(source_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env,
                check=False,
            )

    def test_valid_code_without_py_compile(self):
        result = self.run_validator(b'def hello():\n    return 42\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('bez py_compile', result.stdout)

    def test_syntax_error_is_still_rejected(self):
        result = self.run_validator(b'def broken(:\n    pass\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('main.py', result.stderr)

    def test_old_compileall_dependency_is_gone(self):
        self.assertNotIn('python3 -m compileall', self.installer)
        self.assertIn('validate_python_tree "$SRC_DIR"', self.installer)
        self.assertIn('validate_python_tree "$PLUGIN_DST"', self.installer)


if __name__ == '__main__':
    unittest.main()
