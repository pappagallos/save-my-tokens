"""Request routing and CLI dispatch. No model call is needed to choose a tier."""
import argparse
import json
import re
import subprocess
import sys

from catalog import ACP, ALIASES, ENGINES, TIERS, binary, listed, pick
from acp import Session


FOCUSED = re.compile(r"screenshot|screen ?shot|visual(?:ly)? inspect|single[- ](?:file|function)|one (?:file|function)|typo|rename (?:this|a) (?:field|variable)|targeted fix|스크린샷|화면.?캡처|화면.{0,6}(확인|분석)|오탈자|오타|단일.?파일|한.?파일|한.?함수|함수.?하나|변수명.{0,6}변경|截图|单个?文件|错别字|スクリーンショット|単一ファイル|誤字", re.I)
DEEP = re.compile(r"race condition|deadlock|root cause|distributed|cross.service|architecture|security audit|data loss|concurren|intermittent|근본.?원인|아키텍처|교착|동시성|경쟁.?상태|데이터.?유실|간헐|분산.?시스템|根因|架构|并发|竞态|競合|並行性|設計判断", re.I)
STANDARD = re.compile(r"implement|refactor|debug|write code|fix|design|구현|수정|리팩터|디버깅|설계|개발|实现|修复|重构|実装|修正|リファクタ", re.I)
LIGHT = re.compile(r"summar|translat|extract|classif|format|list the|missing key|failure code|요약|번역|추출|분류|목록|오류.?코드|실패.?코드|누락된.?키|要約|翻訳|抽出|列出|摘要|翻译|提取", re.I)
CONTINUE = re.compile(r"\s*(continue|go on|yes|proceed|계속.{0,4}|이어서.{0,4}|다음|응|진행해|继续|繼續|続けて)[.!?。！ ]*\s*", re.I)


def tier_for(prompt, previous=None):
    if previous and CONTINUE.fullmatch(prompt):
        return previous
    for tier, words in (("deep", DEEP), ("focused", FOCUSED), ("standard", STANDARD), ("light", LIGHT)):
        if words.search(prompt):
            return tier
    return "standard"


def choose(prompt, engine="codex", models=None, override=None, previous=None, available=None):
    tier = tier_for(prompt, previous)
    if override:
        return tier, override
    if models:
        return tier, models[TIERS.index(tier)]
    if engine in ALIASES:
        alias = ALIASES[engine][TIERS.index(tier)]
        if available is None or (engine == "claude" and alias in available):
            return tier, alias
    return tier, pick(listed(engine) if available is None else available, tier, engine)


def report_route(tier, model):
    print(f"[save-my-tokens] {tier} → {model}", file=sys.stderr)


def run_turn(prompt, model, session=None):
    cmd = ["codex", "exec", "--json"]
    if session:
        cmd += ["resume", "-m", model, "--", session, prompt]
    else:
        cmd += ["-m", model, "--", prompt]
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
    completed = False
    try:
        for line in proc.stdout:
            event = json.loads(line)
            kind = event.get("type")
            if kind == "thread.started":
                session = event["thread_id"]
            item = event.get("item", {})
            if kind == "item.completed" and item.get("type") == "agent_message":
                print(item["text"], flush=True)
            if kind == "turn.completed":
                completed = True
            if kind in ("error", "turn.failed"):
                print(event.get("message") or event.get("error"), file=sys.stderr)
        if proc.wait() or not completed:
            raise RuntimeError("Codex did not complete the task")
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
        proc.stdout.close()
    if not session:
        raise RuntimeError("Codex returned no thread ID")
    return session


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["task", "chat", "route", "models"])
    parser.add_argument("--engine", choices=ENGINES)
    parser.add_argument("--host", choices=["replit", "rovodev", "veto"], help="project host using an explicitly selected external engine")
    parser.add_argument("--model", help="explicit model override")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tiers", nargs=4, metavar=("LIGHT", "FOCUSED", "STANDARD", "DEEP"))
    group.add_argument("--models", nargs=3, metavar=("LIGHT", "STANDARD", "DEEP"))
    parser.add_argument("prompt", nargs="?")
    args = parser.parse_intermixed_args(argv)
    if args.host and not args.engine:
        parser.error("select the provider explicitly with --engine when running from this host")
    args.engine = args.engine or "codex"
    if args.host == "veto" and args.mode == "task" and args.engine not in ("codex", "claude"):
        parser.error("Veto native start supports --engine codex or claude")
    if args.tiers:
        args.models = args.tiers
    elif args.models:
        light, standard, deep = args.models
        args.models = [light, standard, standard, deep]
    if args.mode not in ("chat", "models") and not (args.prompt or "").strip():
        parser.error("provide a task")
    agent = None
    try:
        if args.engine in ACP:
            agent = Session(ACP[args.engine])
        elif ((args.mode == "chat" and args.engine != "codex") or
              (args.engine == "gemini" and not (args.model or args.models))):
            commands = {"claude": ["claude-agent-acp"], "gemini": ["gemini", "--acp"],
                        "grok": ["grok", "agent", "stdio"]}
            if args.engine == "cursor":
                cli = binary("cursor")
                help_text = subprocess.check_output([cli, "--help"], text=True, timeout=10)
                if not re.search(r"^\s+acp\b", help_text, re.M):
                    raise ValueError("install a Cursor Agent CLI with the acp command")
                cmd = [cli, "acp"]
            else:
                cmd = commands[args.engine]
            agent = Session(cmd)
        if agent:
            agent.start()
        dispatch(args, agent)
    finally:
        if agent:
            agent.close()


def dispatch(args, agent):
    if args.mode == "models":
        if agent:
            catalog, source = agent.labels, "ACP session model picker"
        elif args.engine in ALIASES:
            catalog, source = list(dict.fromkeys(ALIASES[args.engine])), "provider aliases"
        else:
            catalog, source = listed(args.engine), "installed CLI model list"
        probes = ("extract", "single file fix", "implement", "root cause")
        selections = {}
        errors = {}
        for q in probes:
            tier = tier_for(q)
            try:
                _, model = choose(q, args.engine, args.models, args.model, available=catalog)
                if agent and model not in catalog:
                    raise ValueError(f"{model} is absent from the current model picker")
                selections[tier] = model
            except ValueError as exc:
                errors[tier] = str(exc)
        print(json.dumps({"engine": args.engine, "source": source, "available": catalog,
                          "selected": selections, "unavailable": errors}, ensure_ascii=False, indent=2))
        return
    session = previous = None
    prompt = args.prompt
    while True:
        if prompt is None:
            try:
                prompt = input("you> ").strip()
            except EOFError:
                return
            if prompt == "/exit":
                return
            if not prompt:
                prompt = None
                continue
        tier, model = choose(prompt, args.engine, args.models, args.model, previous,
                             agent.labels if agent else None)
        if agent and model not in agent.ids:
            raise ValueError(f"{model} is absent from the current model picker")
        report_route(tier, model)
        if args.mode == "route":
            print(model)
            return
        if args.host == "veto" and args.mode == "task":
            subprocess.run(["veto", "start", "--agent", args.engine, "--model", model, "--", prompt], check=True)
        elif agent:
            agent.turn(prompt, model)
        elif args.engine == "codex":
            session = run_turn(prompt, model, session)
        else:
            cli = binary(args.engine)
            if args.engine in ("claude", "cursor"):
                cmd = [cli, "--model", model, "-p", "--", prompt]
            else:
                cmd = [cli, "--model", model, "--prompt=" + prompt] if args.engine == "gemini" else [
                    cli, "--model", model, "--single=" + prompt]
            subprocess.run(cmd, stdin=subprocess.DEVNULL, check=True)
        if args.mode != "chat":
            return
        previous, prompt = tier, None


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError) as exc:
        sys.exit(str(exc))
