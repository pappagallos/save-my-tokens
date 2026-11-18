"""Render project-local native subagents without reading host configuration."""

from collections.abc import Mapping
import json
import re


AGENT_DIRECTORIES = {
    "claude": ".claude/agents",
    "cursor": ".cursor/agents",
    "gemini": ".gemini/agents",
    "copilot": ".github/agents",
    "opencode": ".opencode/agents",
}
NATIVE_HOSTS = frozenset(AGENT_DIRECTORIES)
DEFAULT_MODELS = {"claude": ("haiku", "sonnet", "opus")}

ROLE_DESCRIPTIONS = {
    "light": (
        "Use proactively for an independent, bounded read-only task like finding files, "
        "tracing a simple call, or extracting evidence from large output."
    ),
    "standard": (
        "Use proactively for an independent, clearly scoped implementation or repair "
        "with assigned files and an explicit expected result."
    ),
    "deep": (
        "Use proactively for independent read-only investigation of a difficult root cause, "
        "cross-module behavior, or subtle correctness risk."
    ),
}
ROLE_TASKS = {
    "light": "Locate or extract the requested evidence without changing project state.",
    "standard": "Implement the bounded change within the assigned files and run authorized checks.",
    "deep": "Trace the difficult paths without changing project state. Test competing explanations against evidence.",
}


def profiles(host, models=None):
    """Return project-relative paths mapped to text for light, standard and deep roles.

    Accept model IDs as an ordered sequence or a mapping keyed by role. Hosts
    without a default require three IDs available in the user's installation.
    """
    if host not in NATIVE_HOSTS:
        raise ValueError(f"native worker profiles are unavailable for {host}")
    if models is None:
        models = DEFAULT_MODELS.get(host)
        if models is None:
            raise ValueError(f"{host} requires --worker-models LIGHT STANDARD DEEP")
    if isinstance(models, Mapping):
        if set(models) != set(ROLE_DESCRIPTIONS):
            raise ValueError("worker model mapping must have light, standard and deep keys")
        models = [models[role] for role in ROLE_DESCRIPTIONS]
    if not isinstance(models, (list, tuple)) or len(models) != len(ROLE_DESCRIPTIONS):
        raise ValueError("give three worker models in LIGHT STANDARD DEEP order")
    if any(not isinstance(model, str) or not model or model != model.strip()
           or not model.isprintable() or model.casefold() in {"inherit", "auto"}
           for model in models):
        raise ValueError("each worker model must be an explicit model ID or supported alias")
    if host == "opencode" and any(not re.fullmatch(r"[^/\s#]+/[^\s#]+(?:#[^\s#]+)?", model)
                                   for model in models):
        raise ValueError("OpenCode worker model IDs must use provider/model with an optional #variant")

    files = {}
    for (role, description), model in zip(ROLE_DESCRIPTIONS.items(), models):
        name = f"smt-{role}"
        extension = ".agent.md" if host == "copilot" else ".md"
        fields = [f"description: {json.dumps(description)}"]
        if host == "opencode":
            # V2 loads V1 agent files and translates these fields. Keep one
            # representation so projects can use either installed major version.
            model, _, variant = model.partition("#")
            fields.append("mode: subagent")
            if variant:
                fields.append(f"variant: {json.dumps(variant)}")
        else:
            fields.insert(0, f"name: {name}")
        fields.append(f"model: {json.dumps(model)}")
        if host == "copilot":
            fields.extend(("infer: true", "model-policy: required", "include-custom-instructions: true"))
        if role != "standard":
            fields.extend(READ_ONLY_FIELDS[host])
        guidance = (
            "Follow the parent assignment, repository instructions and active approval rules. "
            "Work only within the agreed scope. Do not delegate again. "
            "Return concise findings with file paths, checks, and open issues "
            "for the parent to verify."
        )
        file_path = f"{AGENT_DIRECTORIES[host]}/{name}{extension}"
        files[file_path] = "\n".join(["---", *fields, "---", "", ROLE_TASKS[role], "", guidance, ""])
    return files


READ_ONLY_FIELDS = {
    "claude": ('tools: ["Read", "Grep", "Glob"]',),
    "cursor": ("readonly: true",),
    "gemini": ('tools: ["read_file", "grep_search", "glob", "list_directory"]',),
    "copilot": ('tools: ["read", "grep", "glob"]', "strict-tools-list: true"),
    "opencode": (
        "permission:",
        "  edit: deny",
        "  bash: deny",
        "  task: deny",
        "  execute: deny",
        "  experimental_image_generate: deny",
        "  opencode_session_move: deny",
        "  opencode_session_rename: deny",
        "  opencode_worktree_create: deny",
    ),
}
