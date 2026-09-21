"""DEPRECATED compatibility entry: runs the guarded final verification once.

Old alias-based restoration was unsafe. Historical source remains in Git;
old evidence is preserved. Requires no PIE and clean target packages.
"""
import runpy
from pathlib import Path

_extension_final = runpy.run_path(str(Path(__file__).resolve().with_name('verify_skill_extension_final.py')))
print('DEPRECATED probe_skill_extension: using guarded final verification')
_extension_final['start']()
