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


def test_compile_input_has_direct_deps_hf_packages_and_torch_pin():
    inp = bs.space_requirements_input("6.31.0")
    assert f"torch=={bs.SPACE_TORCH_VERSION}" in inp
    assert [i for i in inp if i.startswith("torch")] == [f"torch=={bs.SPACE_TORCH_VERSION}"]  # local torch constraint dropped
    assert "gradio[oauth,mcp]==6.31.0" in inp
    for pkg in bs.HF_PACKAGES:
        assert pkg in inp
    assert any(i.startswith("anthropic") for i in inp) and any(i.startswith("sentence-transformers") for i in inp)


def test_generated_requirements_are_zerogpu_safe_and_resolve_with_hf_packages():
    sdk = bs.pinned_gradio()
    reqs = bs.export_requirements(sdk)
    lines = reqs.splitlines()
    assert [ln for ln in lines if ln.startswith("torch==")] == [f"torch=={bs.SPACE_TORCH_VERSION}"]
    assert "+cpu" not in reqs and "index-url" not in reqs
    assert f"gradio=={sdk}" in lines and any(ln.startswith("spaces==") for ln in lines)
    assert any(ln.startswith("sentence-transformers==") for ln in lines)
    pyd = next(ln for ln in lines if ln.startswith("pydantic=="))
    assert tuple(map(int, pyd.split("==")[1].split("."))) <= (2, 12, 5)  # gradio[mcp] 6.31.0 requires pydantic<=2.12.5
    bs.check_against_hf(reqs, sdk)  # exits if it does not resolve together with the Hugging Face install command


def test_check_requirements_flags_cpu_index_and_missing_pins():
    ok = f"torch=={bs.SPACE_TORCH_VERSION}\ngradio==6.31.0\n"
    assert bs.check_requirements(ok, "6.31.0") == []
    assert bs.check_requirements("--extra-index-url https://x\ntorch==2.15.0+cpu\n", "6.31.0")
    assert bs.check_requirements("gradio==6.31.0\n", "6.31.0")  # torch pin missing


def test_unsatisfiable_set_makes_the_script_stop():
    with pytest.raises(SystemExit):
        bs.uv_compile(["pydantic==2.14.3", "gradio[mcp]==6.31.0"])


def test_sdk_version_is_read_from_space_readme():
    assert bs.sdk_version_of(HEAD) == "6.31.0"


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
    assert top == {".git", "README.md", "LICENSE", "app.py", "src", "data", "requirements.txt", ".gitignore"}
    assert {p.name for p in (tmp_path / "data").iterdir()} == {"processed", "examples.json"}
    assert (tmp_path / "README.md").read_text().startswith(HEAD)


def test_missing_space_dir_stops_with_clear_message(monkeypatch):
    import os
    env = {k: v for k, v in os.environ.items() if k != "SPACE_DIR"}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_space.py"), "--dry-run"],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    assert r.returncode != 0 and "SPACE_DIR" in r.stderr and "--space-dir" in r.stderr


def test_space_dir_from_environment(tmp_path):
    import os
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text(HEAD + "body\n")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_space.py"), "--dry-run"],
                       capture_output=True, text=True, cwd=ROOT, env={**os.environ, "SPACE_DIR": str(tmp_path)})
    assert r.returncode == 0, r.stderr
