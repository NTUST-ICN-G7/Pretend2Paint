"""維護 coding agent workspace 的設定檔。

用法：
    uv run python scripts/agent_workspace.py sync    # 把 .agents/skills 同步到 .claude/skills
    uv run python scripts/agent_workspace.py check   # 檢查設定檔是否一致（CI / pre-commit 使用）

規則：
- `.agents/skills/` 是 skills 的唯一來源；`.claude/skills/` 是給 Claude Code 的副本，不要手改。
- 每個 `AGENTS.md` 旁邊都要有內容為 `@AGENTS.md` 的 `CLAUDE.md`。
- repo 內不可有 `AGENTS.override.md`（會取代團隊規則）。
- 每個 skill 目錄直接放在 `skills/` 底下（不可再巢狀），且 `SKILL.md` 要有 name 與 description。
"""

from __future__ import annotations

import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / ".agents" / "skills"
MIRROR = ROOT / ".claude" / "skills"
CLAUDE_STUB = "@AGENTS.md\n"


def _repo_files(pattern: str) -> list[Path]:
    """列出 repo 中符合 pattern 的檔案（含尚未 commit 的檔案，排除被忽略的）。"""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", f"*{pattern}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [ROOT / p for p in out.splitlines() if Path(p).name == pattern and (ROOT / p).exists()]


def _frontmatter(skill_md: Path) -> dict[str, str]:
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta


def _dirs_equal(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(_dirs_equal(a / d, b / d) for d in cmp.common_dirs)


def sync() -> int:
    if MIRROR.exists():
        shutil.rmtree(MIRROR)
    shutil.copytree(SOURCE, MIRROR)
    print(f"synced {SOURCE.relative_to(ROOT)} -> {MIRROR.relative_to(ROOT)}")
    return 0


def check() -> int:
    errors: list[str] = []

    # 1. 每個 AGENTS.md 旁邊都要有 CLAUDE.md stub
    for agents_md in _repo_files("AGENTS.md"):
        claude_md = agents_md.with_name("CLAUDE.md")
        rel = claude_md.relative_to(ROOT)
        if not claude_md.exists():
            errors.append(f"missing {rel} (should contain '@AGENTS.md')")
        elif claude_md.read_text(encoding="utf-8") != CLAUDE_STUB:
            errors.append(f"{rel} must contain exactly '@AGENTS.md' (put rules in AGENTS.md)")

    # 2. 不允許 AGENTS.override.md：Codex / Pi 會用它取代同目錄的 AGENTS.md，繞過團隊規則
    for override in _repo_files("AGENTS.override.md"):
        errors.append(
            f"{override.relative_to(ROOT)}: AGENTS.override.md replaces team rules; "
            "put personal rules in your global agent config instead"
        )

    # 3. skills 格式
    for entry in sorted(SOURCE.iterdir()):
        rel = entry.relative_to(ROOT)
        if not entry.is_dir():
            errors.append(f"{rel}: skills must be directories containing SKILL.md")
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{rel}: missing SKILL.md (skills cannot be nested deeper)")
            continue
        meta = _frontmatter(skill_md)
        if meta.get("name") != entry.name:
            errors.append(
                f"{skill_md.relative_to(ROOT)}: frontmatter 'name' must be '{entry.name}'"
            )
        if not meta.get("description"):
            errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter 'description' is required")

    # 4. .claude/skills 與 .agents/skills 一致
    if not MIRROR.exists() or not _dirs_equal(SOURCE, MIRROR):
        errors.append(
            ".claude/skills is out of sync with .agents/skills; "
            "run: uv run python scripts/agent_workspace.py sync"
        )

    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if not errors:
        print("agent workspace OK")
    return 1 if errors else 0


def main() -> int:
    commands = {"sync": sync, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print(__doc__, file=sys.stderr)
        return 2
    return commands[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
