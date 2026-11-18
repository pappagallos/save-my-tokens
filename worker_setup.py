"""Install native worker definitions and configure host-owned routing when supported."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

from native_profiles import DEFAULT_MODELS, NATIVE_HOSTS, profiles
from other_hosts import OTHER_GUIDES, OTHER_NEED_MODELS, OTHER_PROFILE_HOSTS, other_hosts


GROK_RULE = """Use native subagents for independent work when it materially helps the request.
Choose explore for bounded read-only searches, general-purpose for an independent
implementation, and plan for a difficult design question. Keep the main agent on
the selected model. Respect project rules, verify the result, and handle trivial
tasks directly. Workers should finish their own task without creating workers.
"""
GROK_SOURCE = "https://docs.x.ai/build/settings/reference"
DEVIN_SOURCE = "https://docs.devin.ai/cli/adaptive"
REPLIT_SOURCE = "https://docs.replit.com/features/agent/agent-modes"


def discover(host, project):
    script = Path(__file__).parent / "plugins/save-my-tokens/skills/focus-output/scripts/routing.py"
    result = subprocess.run([sys.executable, str(script), "models", "--engine", host],
                            cwd=project, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            timeout=75)
    if result.returncode:
        raise ValueError(f"{host}: no usable model list. Sign in to its current CLI or supply "
                         "--worker-models LIGHT STANDARD DEEP from its worker model picker.")
    data = json.loads(result.stdout)
    selected = data["selected"]
    if any(kind not in selected for kind in ("light", "standard", "deep")):
        raise ValueError(f"{host}: incomplete worker model selection. Supply --worker-models LIGHT STANDARD DEEP.")
    return [selected[kind] for kind in ("light", "standard", "deep")]


def direct_path(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError(f"invalid installation path: {relative}")
    path = root
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"choose a direct installation path: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"expected a regular file at {path}")
    return path


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        staging = Path(tmp.name)
    try:
        staging.write_bytes(text.encode("utf-8"))
        if path.exists():
            staging.chmod(stat.S_IMODE(path.stat().st_mode))
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_profiles(project, skill, host, files):
    receipt = direct_path(project, skill.relative_to(project) / f".workers-{host}.json")
    previous = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
    changes = {}
    for name, text in files.items():
        path = direct_path(project, name)
        if path.exists():
            original = path.read_bytes()
            if original == text.encode("utf-8"):
                continue
            if previous.get(name) != digest(original):
                raise ValueError(f"existing worker differs at {path}; preserve or move your version before installing")
        changes[path] = text
    for path, text in changes.items():
        write_text(path, text)
    updated = {**previous, **{name: digest(text.encode("utf-8")) for name, text in files.items()}}
    if updated != previous:
        write_text(receipt, json.dumps(updated, indent=2, sort_keys=True) + "\n")


def grok_models(path, models):
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            raise ValueError("Grok personal settings require Python 3.11+ or tomli on Python 3.9/3.10") from None
    if len(models) != 3 or any(not m or not m.isprintable() or m.strip() != m for m in models):
        raise ValueError("supply three available Grok worker model IDs")
    table = dict(zip(("explore", "general-purpose", "plan"), models))
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    parsed = tomllib.loads(old)
    subagents = parsed.get("subagents", {})
    if not isinstance(subagents, dict) or not isinstance(subagents.get("models", {}), dict):
        raise ValueError(f"expected a subagents.models table in {path}")
    if subagents.get("enabled") is False:
        raise ValueError("Grok subagents are disabled in your settings. Enable them to use role models.")
    existing = subagents.get("models", {})
    if all(existing.get(k) == v for k, v in table.items()):
        return
    # Preserve comments, custom roles and unrelated tables. For inline or dotted
    # representations, ask for a table edit instead of reserializing the document.
    header = re.search(r"(?m)^\s*\[\s*subagents\.models\s*\][ \t]*(?:#[^\n]*)?$", old)
    start = header.end() if header else len(old)
    following = re.search(r"(?m)^[ \t]*\[", old[start:]) if header else None
    end = start + following.start() if following else len(old)
    body = old[start:end]
    for key, value in table.items():
        pattern = rf"(?m)^([ \t]*(?:{key}|\"{key}\"|'{key}')[ \t]*=[ \t]*)(?:\"(?:\\.|[^\"\\])*\"|'[^'\n]*')([ \t]*(?:#[^\n]*)?)$"
        quoted = json.dumps(value, ensure_ascii=False)
        if re.search(pattern, body):
            body = re.sub(pattern, lambda match: match[1] + quoted + match[2], body)
        else:
            body = body.rstrip("\n") + f"\n{key} = {quoted}\n"
    updated = old[:start] + ("" if header else "\n[subagents.models]") + body.rstrip("\n") + "\n" + old[end:]
    expected = {**parsed, "subagents": {**subagents, "models": {**existing, **table}}}
    try:
        valid = tomllib.loads(updated) == expected
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"edit the existing subagents.models representation in {path}; "
                         "the installer could not preserve it safely")
    return updated


def enable_devin(path):
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(existing, dict) or not isinstance(existing.get("agent", {}), dict):
        raise ValueError(f"expected a JSON object with an agent object in {path}")
    agent = existing.setdefault("agent", {})
    if agent.get("model") != "adaptive":
        agent["model"] = "adaptive"
        write_text(path, json.dumps(existing, indent=2, ensure_ascii=False) + "\n")


MAIN_GUIDANCE = """The user requests automatic delegation when native smt workers are available.
On requests with independent work, start the appropriate worker before taking the
remaining work yourself. For example, when given two independent investigations,
assign one to smt-light (bounded evidence) or smt-deep (difficult investigation).
Use smt-standard for a bounded implementation. Keep simple work and final integration
with the main agent. Respect project restrictions and any request to work alone.
Workers must complete their own assignment without starting further workers.
"""


def parent_guidance(host, project, files):
    if host == "claude":
        files[".claude/rules/smt-workers.md"] = MAIN_GUIDANCE
    elif host == "cursor":
        files[".cursor/rules/smt-workers.mdc"] = "---\nalwaysApply: true\n---\n\n" + MAIN_GUIDANCE
    common = {"gemini": "GEMINI.md", "copilot": ".github/copilot-instructions.md", "opencode": "AGENTS.md"}
    if host not in common:
        return None
    path = direct_path(project, common[host])
    original = path.read_bytes().decode("utf-8") if path.exists() else ""
    start = f"<!-- save-my-tokens: {host} workers -->"
    end = f"<!-- /save-my-tokens: {host} workers -->"
    block = f"{start}\nWhen running as the main {host} agent:\n{MAIN_GUIDANCE}{end}"
    newline = "\r\n" if "\r\n" in original else "\n"
    block = block.replace("\n", newline)
    if start in original or end in original:
        if original.count(start) == original.count(end) == 1 and block in original:
            return None
        raise ValueError(f"existing worker instructions were edited in {path}; preserve or move that block first")
    return path, original + (newline * 2 if original else "") + block + newline


def setup(host, project, skill, models=None, user_settings=False):
    project = project.resolve(strict=True)
    if user_settings and host not in ("devin", "grok"):
        raise ValueError("--user-settings applies only to Grok and Devin")
    if host in NATIVE_HOSTS or host in OTHER_PROFILE_HOSTS:
        needs_models = host in NATIVE_HOSTS - DEFAULT_MODELS.keys() or host in OTHER_NEED_MODELS
        if needs_models and not models:
            models = discover(host, project)
        files = profiles(host, models) if host in NATIVE_HOSTS else other_hosts(host, models)
        shared = parent_guidance(host, project, files)
        write_profiles(project, skill, host, files)
        if shared:
            write_text(*shared)
        message = f"Installed {len(files)} native definitions for {host}."
        if host in OTHER_GUIDES:
            message += " " + OTHER_GUIDES[host][1]
        return message
    if host == "grok":
        if models and not user_settings:
            raise ValueError("Grok reads worker model IDs only from personal settings. Add --user-settings.")
        pending = None
        if user_settings:
            base = Path(os.environ.get("GROK_HOME", Path.home() / ".grok"))
            config_path = direct_path(base.resolve(), "config.toml")
            pending = grok_models(config_path, models or discover(host, project))
        write_profiles(project, skill, host, {".grok/rules/save-my-tokens-workers.md": GROK_RULE})
        if pending is not None:
            write_text(config_path, pending)
        state = "Personal worker model map configured." if user_settings else "Add --user-settings to set role models."
        return f"Installed Grok project delegation rules. {state} {GROK_SOURCE}"
    if models:
        raise ValueError(f"{host} does not accept installer-supplied worker model IDs.")
    if host == "devin":
        if user_settings:
            base = Path(os.environ["APPDATA"]) / "devin" if os.name == "nt" else Path.home() / ".config/devin"
            enable_devin(direct_path(base.resolve(), "config.json"))
            return f"Set Devin personal agent.model to adaptive. Enterprise policy may restrict selection. {DEVIN_SOURCE}"
        return f"Host action required: enter /model adaptive in Devin, or add --user-settings for the personal default. {DEVIN_SOURCE}"
    if host == "replit":
        return f"Host action required: use Free Mode, or choose Auto in Power/Max where available. {REPLIT_SOURCE}"
    if host == "codex":
        return ("Codex uses its native plugin switch. From this checkout run codex plugin marketplace add . and "
                "codex plugin add save-my-tokens-auto@save-my-tokens-local, set the standing preference in "
                "~/.codex/AGENTS.md as shown in the README, then start a new conversation.")
    source, instructions = OTHER_GUIDES[host]
    return f"Host action required: {instructions} {source}"
