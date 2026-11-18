"""Obtain model IDs from the installed host. Rank versions within a family."""
import json
import re
import shutil
import subprocess

TIERS = ("light", "focused", "standard", "deep")
ALIASES = {"claude": ("haiku", "sonnet", "sonnet", "opus"), "gemini": ("flash-lite", "flash", "flash", "pro")}
ACP = {
    "copilot": ("copilot", "--acp"), "devin": ("devin", "acp"),
    "opencode": ("opencode", "acp"), "antigravity": ("agy_acp_server.par",),
    "kiro": ("kiro-cli", "acp"), "qoder": ("qodercli", "--acp"),
    "vibe": ("vibe-acp",), "pi": ("pi-acp",), "hermes": ("hermes", "acp"),
    "omp": ("omp", "acp"), "deepseek": ("dsh", "--profile", "acp"),
    "trae": ("traecli", "acp", "serve"), "trae-cn": ("traecli", "acp", "serve"),
}
ENGINES = ("codex", "cursor", "grok", *ALIASES, *ACP)

# Ordered families are a local routing policy. Compare version numbers only within
# the same family. Never send an invented model ID or compare vendors' version numbers.
FAMILIES = {
    "light": ("luna", "haiku", "flash-lite", "mini", "small", "lite", "efficient", "flash", "fast", "instant"),
    "focused": ("terra", "flash", "sonnet", "composer", "build", "efficient", "coder", "devstral", "mini"),
    "standard": ("sol", "sonnet", "composer", "build", "devstral", "performance", "flash", "gpt", "grok", "glm", "qwen", "deepseek"),
    "deep": ("astra", "opus", "pro", "ultimate", "reasoner", "reasoning", "thinking", "large", "max", "grok", "gpt", "sonnet"),
}
# Family order describes the task fit, not a comparison of vendor version numbers.
# Each tuple is intersected with the host's advertised catalog at request time.
POLICIES = {
    "codex": (("luna", "nano", "mini"), ("terra", "mini"), ("sol", "codex", "gpt"), ("astra", "pro", "gpt")),
    "claude": (("haiku",), ("sonnet", "haiku"), ("sonnet",), ("opus", "fable")),
    "gemini": (("flash-lite", "flash"), ("flash",), ("flash", "pro"), ("pro",)),
    "cursor": (("mini", "haiku", "flash-lite"), ("composer", "terra"), ("sonnet", "sol", "composer"), ("opus", "astra", "pro")),
    "grok": (("non-reasoning", "fast", "grok"), ("build", "code", "grok"), ("build", "grok"), ("reasoning", "heavy", "grok")),
    "qoder": (("efficient",), ("efficient", "fast"), ("performance", "fast", "auto"), ("ultimate",)),
    "vibe": (("small", "mini"), ("devstral-small", "small", "devstral"), ("devstral", "medium"), ("large", "medium", "devstral")),
    "deepseek": (("flash",), ("flash", "coder"), ("pro", "chat"), ("pro", "reasoner")),
    "devin": (("haiku", "fast"), ("swe", "terra"), ("sonnet", "sol", "swe"), ("opus", "astra", "pro")),
    "copilot": (("mini", "haiku", "luna"), ("terra", "flash", "sonnet"), ("sol", "sonnet", "gpt"), ("astra", "opus", "pro")),
    "trae": (("flash", "mini", "haiku"), ("coder", "seed", "flash", "sonnet"), ("sonnet", "glm", "qwen", "kimi"), ("opus", "pro", "reasoner", "thinking")),
    "kiro": (("haiku",), ("sonnet",), ("sonnet",), ("opus",)),
}
POLICIES["trae-cn"] = POLICIES["trae"]
POLICIES["antigravity"] = POLICIES["gemini"]
SHORT = {"light": ("focused", "standard", "deep"), "focused": ("standard", "light", "deep"),
         "standard": ("focused", "deep", "light"), "deep": ("standard", "focused", "light")}
NON_CHAT = re.compile(r"(embed|moderation|transcri|whisper|tts|image|video|audio|realtime|vision-only|rerank|guard|multi-agent)")


def binary(engine):
    if engine == "cursor":
        for name in ("agent", "cursor-agent"):
            found = shutil.which(name)
            if found and ("cursor" in name or "cursor" in subprocess.run(
                    [found, "--help"], capture_output=True, text=True, timeout=8).stdout.lower()):
                return found
        raise ValueError("install the Cursor Agent CLI and sign in")
    return engine


def listed(engine):
    args = {"codex": ["debug", "models"], "cursor": ["--list-models"], "grok": ["models"]}[engine]
    cmd = [binary(engine), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    if result.returncode:
        raise ValueError(f"{' '.join(cmd)} failed. Check CLI version and sign-in, or supply --tiers LIGHT FOCUSED STANDARD DEEP.")
    if engine == "codex":
        data = json.loads(result.stdout)
        rows = data if isinstance(data, list) else data["models"]
        return [r["slug"] for r in rows if r.get("visibility") == "list"]
    clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)
    ids = []
    for line in clean.splitlines():
        match = re.match(r"^\s*[│*•>\s]*([a-z0-9][a-z0-9._:/-]*-[a-z0-9._:/-]+)(?=\s|$)", line)
        if match:
            ids.append(match[1])
    return list(dict.fromkeys(ids))


def pick(ids, tier, engine=None):
    labels = ids if isinstance(ids, dict) else {}
    eligible = [i for i in ids if not NON_CHAT.search((i + " " + labels.get(i, "")).lower())]
    if not eligible:
        raise ValueError("no selectable text model advertised; check sign-in and the host's model picker")
    if len(eligible) == 1:
        return eligible[0]
    for bucket in (tier, *SHORT[tier]):
        preferred = POLICIES[engine][TIERS.index(bucket)] if engine in POLICIES else ()
        for family in dict.fromkeys((*preferred, *FAMILIES[bucket])):
            candidates = []
            for ident in eligible:
                name = ident.rsplit("/", 1)[-1].lower()
                label = re.sub(r"[^a-z0-9.]+", "-", labels.get(ident, "").lower()).strip("-")
                parts = re.split(r"[-_.:/]", name)
                pattern = r"(?:^|[-_.:/])" + family + r"(?:$|[-_.:/0-9])"
                if not re.search(pattern, name):
                    name = label
                    parts = re.split(r"[-_.:/]", name)
                if not re.search(pattern, name):
                    continue
                if (family == "flash" and "lite" in parts) or (bucket == "deep" and "non" in parts and "reasoning" in parts):
                    continue
                if family in ("gpt", "grok", "deepseek") and any(x in parts for x in ("mini", "nano", "fast", "lite")) and bucket != "light":
                    continue
                version = tuple(map(int, re.findall(r"\d+", name)))
                candidates.append((version, -len(name), ident))
            if candidates:
                return max(candidates)[2]
    raise ValueError("unrecognized model families. Use --tiers with four IDs from the host's model picker")
