"""Section 4: the Space sync script keeps the Space README header and refuses unsafe situations."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_space", ROOT / "scripts" / "build_space.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

HEAD = "---\ntitle: X\nsdk: gradio\nsdk_version: 6.31.0\napp_file: app.py\n---\n"


def test_readme_header_is_kept_byte_for_byte():
    out = bs.space_readme(HEAD + "old body that gets replaced\n")
    assert out.startswith(HEAD) and "old body" not in out
    assert "Not legal advice" in out and "IEC 62304" in out and "EUR-Lex" in out


def test_readme_without_header_is_refused():
    with pytest.raises(SystemExit):
        bs.space_readme("# just text\n")


def test_sdk_version_mismatch_is_refused():
    with pytest.raises(SystemExit):
        bs.space_readme(HEAD.replace("6.31.0", "5.0.0"))


def test_requirements_exclude_gradio_and_use_cpu_torch_index():
    reqs = bs.export_requirements()
    assert reqs.startswith("--extra-index-url https://download.pytorch.org/whl/cpu")
    assert "gradio" not in reqs and "nvidia" not in reqs and "torch==" in reqs


def test_dry_run_into_fake_space_writes_nothing(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text(HEAD + "body\n")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_space.py"), "--space-dir", str(tmp_path), "--dry-run"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in tmp_path.iterdir()) == [".git", "README.md"]


def test_sync_copies_only_allowed_files(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text(HEAD + "body\n")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_space.py"), "--space-dir", str(tmp_path)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    top = {p.name for p in tmp_path.iterdir()}
    assert top == {".git", "README.md", "app.py", "src", "data", "requirements.txt", ".gitignore"}
    assert {p.name for p in (tmp_path / "data").iterdir()} == {"processed", "examples.json"}
    assert (tmp_path / "README.md").read_text().startswith(HEAD)
