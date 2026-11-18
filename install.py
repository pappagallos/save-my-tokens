"""Install the portable project skill for one coding agent. Python 3.9+."""
import argparse
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "plugins/save-my-tokens/skills/focus-output/scripts"
HOSTS = {
    "claude": ".claude", "cursor": ".cursor", "codex": ".agents", "copilot": ".github",
    "devin": ".devin", "replit": ".agents", "gemini": ".gemini", "grok": ".grok",
    "opencode": ".opencode", "antigravity": ".agent", "kiro": ".kiro", "trae": ".trae",
    "trae-cn": ".trae-cn", "rovodev": ".rovodev", "qoder": ".qoder", "vibe": ".vibe",
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
        if all((target / rel).is_file() and (target / rel).read_bytes() == src.read_bytes()
               for rel, src in files.items()):
            return target
        raise ValueError(f"existing skill differs at {target}; move it aside to upgrade")
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
    args = parser.parse_args()
    try:
        print(install(args.platform, args.project))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
