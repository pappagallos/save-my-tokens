"""Install the portable project skill for one coding agent. Python 3.9+."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
import subprocess

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "plugins/save-my-tokens/skills/focus-output/scripts"
HOSTS = {
    "claude": ".claude", "cursor": ".cursor", "codex": ".agents", "copilot": ".github",
    "devin": ".devin", "replit": ".agents", "gemini": ".gemini", "grok": ".grok",
    "opencode": ".opencode", "antigravity": ".agents", "kiro": ".kiro", "trae": ".trae",
    "trae-cn": ".trae", "rovodev": ".rovodev", "qoder": ".qoder", "vibe": ".vibe",
    "pi": ".pi", "hermes": ".hermes", "deepseek": ".dsh", "veto": ".veto",
    "omp": ".omp",
}


def install(host, project):
    root = project.resolve(strict=True)
    parent = root / HOSTS[host] / "skills"
    target = parent / "save-my-tokens"
    if any(p.is_symlink() for p in (parent.parent, parent, target)):
        raise ValueError(f"choose a project with a direct skills directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    files = {Path("SKILL.md"): ROOT / "portable/SKILL.md"}
    files.update({Path("scripts") / p.name: p for p in SCRIPTS.glob("*.py")})
    if target.exists():
        from worker_setup import direct_path, write_text
        updates = []
        # v0.3.0 predates installation receipts. Upgrade only the original published file.
        previous = {"scripts/catalog.py": "e7c6337c35719425a3747a76dd086ef037d5573e9aa3bb59faa5d78c89975e8c"}
        for rel, source in files.items():
            existing = direct_path(target, rel)
            if not existing.is_file():
                raise ValueError(f"existing skill is incomplete at {existing}")
            content = existing.read_bytes()
            if content == source.read_bytes():
                continue
            if previous.get(rel.as_posix()) != hashlib.sha256(content).hexdigest():
                raise ValueError(f"existing skill differs at {existing}; preserve or move your version to upgrade")
            updates.append((existing, source))
        for existing, source in updates:
            write_text(existing, source.read_text(encoding="utf-8"))
        return target
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        staging = Path(tmp) / "skill"
        (staging / "scripts").mkdir(parents=True)
        for rel, src in files.items():
            shutil.copyfile(src, staging / rel)
        staging.rename(target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=sorted(HOSTS), required=True)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--auto-workers", action="store_true",
                        help="install native workers or show the host action required")
    parser.add_argument("--worker-models", nargs=3, metavar=("LIGHT", "STANDARD", "DEEP"),
                        help="three IDs from the host's worker model picker")
    parser.add_argument("--user-settings", action="store_true",
                        help="also update Grok's personal worker map or Devin's personal default")
    args = parser.parse_args()
    if (args.worker_models or args.user_settings) and not args.auto_workers:
        parser.error("--worker-models and --user-settings require --auto-workers")
    try:
        skill = install(args.platform, args.project)
        print(f"Portable skill: {skill}", flush=True)
        if args.auto_workers:
            from worker_setup import setup
            print(setup(args.platform, args.project.resolve(), skill, args.worker_models, args.user_settings))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"{exc}\n")
