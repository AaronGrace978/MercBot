"""The flywheel must stand alone: no import path may reach the runtime or the forge."""

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLYWHEEL = sorted((ROOT / "mercury").glob("*.py"))
RUNTIME = sorted((ROOT / "runtime" / "mercury_runtime").glob("*.py"))
FORGE = sorted((ROOT / "forge" / "mercury_forge").glob("*.py"))

# The CLI is the umbrella entry point and ``mercury/__init__`` lazily re-exports; both load
# the add-ons only on demand and turn a missing package into an install hint.
UMBRELLA = {"cli.py", "__init__.py"}


def _imported_roots(path: Path, *, top_level_only: bool) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = tree.body if top_level_only else list(ast.walk(tree))
    roots: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_flywheel_never_imports_runtime_or_forge():
    offenders = {}
    for path in FLYWHEEL:
        if path.name in UMBRELLA:
            continue
        hit = _imported_roots(path, top_level_only=False) & {"mercury_runtime", "mercury_forge"}
        if hit:
            offenders[path.name] = sorted(hit)
    assert not offenders, offenders


def test_umbrella_modules_only_import_addons_lazily():
    for path in FLYWHEEL:
        if path.name in UMBRELLA:
            hit = _imported_roots(path, top_level_only=True) & {"mercury_runtime", "mercury_forge"}
            assert not hit, (path.name, hit)


def test_runtime_never_imports_forge_at_module_level():
    for path in RUNTIME:
        hit = _imported_roots(path, top_level_only=True) & {"mercury_forge"}
        assert not hit, (path.name, hit)


def test_flywheel_runs_end_to_end_with_only_its_own_path(tmp_path):
    """Fresh interpreter with the add-ons made unimportable: capture, pack, grade and decay all work."""
    script = textwrap.dedent(
        f"""
        import sys

        class _Block:
            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] in ("mercury_runtime", "mercury_forge"):
                    raise ModuleNotFoundError(f"No module named {{name!r}}", name=name)

        sys.meta_path.insert(0, _Block())
        sys.path.insert(0, {str(ROOT)!r})
        import mercury
        from mercury import MercuryHarness
        from mercury.demo import frontier_auth_fix, lesser_auth_fail
        from mercury.grade import grade_trace
        from mercury.cli import main

        h = MercuryHarness.init({str(tmp_path / "s")!r})
        h.capture(frontier_auth_fix())
        h.contrast(lesser_auth_fail(), frontier_auth_fix())
        pack = h.pack("Login keeps redirecting back to /login", model="gpt-4o-mini")
        assert pack.cards
        assert grade_trace(frontier_auth_fix()).score > 0.8
        assert h.store.decay_stale() == []
        assert main(["--store", {str(tmp_path / "s2")!r}, "demo"]) == 0
        try:
            mercury.MercuryAgentRuntime
        except ImportError as exc:
            assert "pip install mercury-runtime" in str(exc)
        else:
            raise SystemExit("runtime unexpectedly importable")
        assert main(["--store", {str(tmp_path / "s3")!r}, "models"]) == 2
        loaded = [m for m in sys.modules if m.startswith(("mercury_runtime", "mercury_forge"))]
        assert not loaded, loaded
        print("flywheel-only ok")
        """
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "flywheel-only ok" in proc.stdout
