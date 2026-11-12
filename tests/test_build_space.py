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


def test_space_requirements_pin_supported_torch_and_drop_cpu_index():
    reqs = bs.export_requirements()
    lines = reqs.splitlines()
    assert [ln for ln in lines if ln.startswith("torch")] == [f"torch=={bs.SPACE_TORCH_VERSION}"]
    assert "+cpu" not in reqs and "index-url" not in reqs
    assert "gradio" not in reqs and "nvidia" not in reqs
    assert any(ln.startswith("sentence-transformers==") for ln in lines)
    assert reqs.endswith("\n") and not reqs.endswith("\n\n")


def test_space_requirements_replace_all_torch_lines():
    exported = (
        "--extra-index-url https://download.pytorch.org/whl/cpu\nnumpy==2.5.4\n"
        "torch==2.14.1 ; sys_platform == 'darwin'\ntorch==2.15.0+cpu ; sys_platform != 'darwin'\ntorchvision==0.1\n"
    )
    out = bs.space_requirements(exported)
    assert out == f"numpy==2.5.4\ntorchvision==0.1\ntorch=={bs.SPACE_TORCH_VERSION}\n"


def test_pinned_torch_is_compatible_with_dependency_constraints():
    from packaging.version import Version

    assert Version(bs.SPACE_TORCH_VERSION) >= Version("2.6")  # transformers needs torch>=2.6, sentence-transformers >=2.2


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
