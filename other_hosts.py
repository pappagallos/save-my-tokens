"""Project-local worker profiles and official setup guides for additional hosts."""

import json

from native_profiles import ROLE_DESCRIPTIONS, ROLE_TASKS


MARKDOWN_HOSTS = {
    "antigravity": ".agents/agents",
    "omp": ".omp/agents",
    "pi": ".pi/agents",
    "qoder": ".qoder/agents",
    "rovodev": ".rovodev/subagents",
    "trae": ".trae/agents",
    "trae-cn": ".trae/agents",
}
OTHER_PROFILE_HOSTS = frozenset(MARKDOWN_HOSTS) | {"kiro", "vibe"}
OTHER_NEED_MODELS = frozenset({"kiro", "omp", "pi", "trae", "trae-cn", "vibe"})
DEFAULT_MODELS = {
    "antigravity": ("flash", "inherit", "pro"),
    "qoder": ("lite", "efficient", "performance"),
}

OTHER_GUIDES = {
    "antigravity": (
        "https://antigravity.google/docs/subagents",
        "Open /agents in the project and check for smt-light, smt-standard, and smt-deep. "
        "The supported worker tiers are flash, inherit, and pro. The standard default inherits your main model.",
    ),
    "kiro": (
        "https://kiro.dev/docs/custom-agents/configuration-reference/",
        "Use IDE 1.x or CLI V3 and supply model IDs from /model. Start a fresh IDE or CLI chat "
        "and ask the main agent to delegate a bounded task by profile name.",
    ),
    "trae": (
        "https://docs.trae.ai/ide/subagents",
        "Use the built-in Agent and pick built-in model IDs from the Subagent documentation. "
        "Turn on Settings > Beta > Subagents > Enable Subagents Directory if it is disabled.",
    ),
    "trae-cn": (
        "https://docs.trae.cn/ide_subagents",
        "Use the built-in Agent and pick built-in model IDs from the Subagent documentation. "
        "If profiles do not load, check Settings > Beta > Subagents > Enable Subagents Directory.",
    ),
    "qoder": (
        "https://docs.qoder.com/cli/subagent",
        "Open a trusted project in Qoder CLI, run /agents reload, and verify the Project tab. "
        "Invoke a worker with @smt-light, @smt-standard, or @smt-deep to check its model.",
    ),
    "vibe": (
        "https://docs.mistral.ai/vibe/code/cli/agents",
        "Open the trusted project in Vibe and choose configured model aliases for active_model. "
        "Start a fresh session and check for model fallback notices when delegating by worker name.",
    ),
    "rovodev": (
        "https://support.atlassian.com/rovo/docs/use-subagents-in-rovo-dev-cli/",
        "Open /subagents, if enabled for your CLI, and edit each installed profile to select its model. "
        "Then ask Rovo Dev to invoke it by name. Installation registers the roles only.",
    ),
    "pi": (
        "https://pi.dev/packages/pi-subagents",
        "Review and install pi-subagents with pi install npm:pi-subagents on Pi 1.2.0 or newer. "
        "Trust this project in Pi and allow project agent discovery. Use /subagents-doctor to check "
        "the extension, then ask Pi to list its subagents. The installer only writes profiles.",
    ),
    "hermes": (
        "https://hermes-agent.nousresearch.com/marketplace/advanced-delegation",
        "On Hermes 0.22.5 or newer, run hermes plugins install advanced-delegation in the delegating "
        "profile. Use hermes delegation config to set named model routes and start a new session.",
    ),
    "deepseek": (
        "https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/feature/2026-08-24-user-authorized-subagent-model-routes.md",
        "In Plugins settings, enable subagent model selection and allow exact provider/model routes. "
        "Start a new session, then ask the parent to delegate with a selected model.",
    ),
    "omp": (
        "https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md",
        "Supply model selectors available in Oh My Pi and verify the profiles in /agents. Ask the main agent to use the task tool "
        "with agent smt-light, smt-standard, or smt-deep.",
    ),
    "veto": (
        "https://github.com/oleg-koval/veto",
        "For oleg-koval/veto, verify installed integrations with veto doctor and use "
        "veto start --choose model --agent <agent> <task> for a new session.",
    ),
}

READ_ONLY_FIELDS = {
    "antigravity": "tools: [view_file, grep_search]",
    "omp": "tools: [read, grep, glob]",
    "pi": "tools: read, grep, find, ls",
    "qoder": "tools: [Read, Grep, Glob]",
    "rovodev": "tools: [open_files, expand_code_chunks, grep]",
    "trae": "tools: Read, Glob, Grep",
    "trae-cn": "tools: Read, Glob, Grep",
}

ROUTING_GUIDANCE = (
    "Keep the current main model and handle direct or trivial work in the main session. "
    "Where the session and repository allow delegation, use smt-light for bounded evidence "
    "gathering, smt-standard for a clearly scoped implementation, and smt-deep for difficult "
    "investigation. Delegate only independent work with clear scope, share the minimum needed "
    "context, and verify the results in the main session. Respect an explicit request to work alone.\n"
)


def other_hosts(host, models=None) -> dict[str, str]:
    """Render project-relative files for one supported host without writing them."""
    if host not in OTHER_PROFILE_HOSTS:
        return {}
    if host == "rovodev" and models is not None:
        raise ValueError("assign Rovo Dev worker models through /subagents")
    if models is None and host in OTHER_NEED_MODELS:
        raise ValueError(f"{host} requires --worker-models LIGHT STANDARD DEEP")

    if models is not None:
        if not isinstance(models, (list, tuple)) or len(models) != len(ROLE_DESCRIPTIONS):
            raise ValueError("give three worker models in LIGHT STANDARD DEEP order")
        if any(not isinstance(model, str) or not model or model != model.strip()
               or not model.isprintable() or model.casefold() == "auto" for model in models):
            raise ValueError("each worker model must be an explicit model ID or supported alias")
        if host == "antigravity" and any(
            model not in {"flash", "inherit", "pro"} for model in models
        ):
            raise ValueError("Antigravity worker tiers must be flash, inherit, or pro")
        if host != "antigravity" and any(model.casefold() == "inherit" for model in models):
            raise ValueError("use explicit worker models for this host")

    files = {}
    models = models or DEFAULT_MODELS.get(host, (None,) * len(ROLE_DESCRIPTIONS))
    for (role, description), model in zip(ROLE_DESCRIPTIONS.items(), models):
        name = f"smt-{role}"
        prompt = (
            f"{ROLE_TASKS[role]} Follow the repository rules and the parent's assignment. "
            "Do not delegate again. Report the result and concise supporting evidence."
        )
        if host == "kiro":
            config = {"name": name, "description": description, "model": model, "prompt": prompt}
            config["tools"] = ["read", "write", "shell"] if role == "standard" else ["read"]
            files[f".kiro/agents/{name}.json"] = json.dumps(config, indent=2) + "\n"
        elif host == "vibe":
            fields = [
                'agent_type = "subagent"',
                f"description = {json.dumps(description)}",
                f"active_model = {json.dumps(model, ensure_ascii=False)}",
                f"instructions = {json.dumps(prompt)}",
            ]
            if role != "standard":
                fields.append('enabled_tools = ["read_file", "grep"]')
            files[f".vibe/agents/{name}.toml"] = "\n".join(fields) + "\n"
        else:
            fields = [f"name: {name}", f"description: {json.dumps(description)}"]
            if model is not None:
                fields.append(f"model: {json.dumps(model)}")
            if host == "antigravity":
                fields.extend(("mainAgent: false", "subagent: true"))
                if role == "standard":
                    fields.append("tools: [view_file, grep_search, replace_file_content, run_command]")
            if host == "rovodev" and role == "standard":
                fields.append("tools: [open_files, expand_code_chunks, grep, bash]")
            if role != "standard":
                fields.append(READ_ONLY_FIELDS[host])
            path = f"{MARKDOWN_HOSTS[host]}/{name}.md"
            files[path] = "---\n" + "\n".join(fields) + f"\n---\n\n{prompt}\n"

    if host == "antigravity":
        files[".agents/rules/smt-workers.md"] = "---\ntrigger: always_on\n---\n\n" + ROUTING_GUIDANCE
    if host == "kiro":
        files[".kiro/steering/smt-workers.md"] = "---\ninclusion: always\n---\n\n" + ROUTING_GUIDANCE
    return files
