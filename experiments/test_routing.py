"""Offline contract checks. No provider logins or model calls."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "plugins/save-my-tokens/skills/focus-output/scripts"))
from acp import Session
from catalog import ACP, listed, pick
from install import HOSTS, install
from routing import choose, main as route


class RoutingTests(unittest.TestCase):
    def test_latest_listed_version(self):
        models = ["gpt-6-luna", "gpt-6.2-sol", "gpt-6.10-sol", "gpt-6.2-astra"]
        self.assertEqual(pick(models, "standard"), "gpt-6.10-sol")
        self.assertEqual(pick(models, "deep"), models[-1])
        self.assertEqual(choose("계속해", previous="deep", available=models), ("deep", models[-1]))
        self.assertEqual(choose("요약", override="explicit"), ("light", "explicit"))
        self.assertEqual(choose("요약", "claude", available=["haiku", "claude-haiku-4-5"])[1], "haiku")
        self.assertEqual(pick(["grok-4-fast-non-reasoning", "grok-4-fast-reasoning"], "deep"), "grok-4-fast-reasoning")
        with self.assertRaises(ValueError):
            pick([], "light")

    def test_provider_families_and_live_updates(self):
        fixtures = {
            "codex": ("gpt-6-luna", "gpt-6.1-terra", "gpt-6.2-sol", "gpt-6.2-astra"),
            "claude": ("haiku", "sonnet", "sonnet", "opus"),
            "gemini": ("gemini-3-flash-lite", "gemini-3-flash", "gemini-3-flash", "gemini-3-pro"),
            "grok": ("grok-4-fast-non-reasoning", "grok-build-0.2", "grok-build-0.2", "grok-4-reasoning"),
            "cursor": ("claude-haiku-5", "composer-2.5", "claude-sonnet-5", "claude-opus-5"),
            "qoder": ("efficient", "efficient", "performance", "ultimate"),
            "vibe": ("mistral-small", "devstral-small", "devstral-2", "mistral-large"),
            "deepseek": ("deepseek-v4-flash", "deepseek-v4-flash", "deepseek-v4-pro", "deepseek-v4-pro"),
            "devin": ("haiku", "swe", "sonnet", "opus"),
        }
        prompts = ("요약", "스크린샷 확인", "기능 구현", "동시성 근본 원인")
        for host, expected in fixtures.items():
            ids = list(dict.fromkeys(expected))
            with self.subTest(host=host):
                self.assertEqual(tuple(choose(q, host, available=ids)[1] for q in prompts), expected)
        self.assertEqual(pick({"opaque0": "Gemini 4 Flash", "opaque9": "Gemini 4 Pro"}, "deep", "gemini"), "opaque9")
        self.assertEqual(choose("single file fix", available=["gpt-6-terra", "gpt-6.10-terra"])[1], "gpt-6.10-terra")
        with patch("routing.subprocess.run") as run:
            route(["task", "--host", "veto", "--engine", "claude", "fix a typo"])
            self.assertEqual(run.call_args.args[0], ["veto", "start", "--agent", "claude", "--model", "sonnet", "--", "fix a typo"])

    def test_native_catalogs_and_dispatch(self):
        answer = subprocess.CompletedProcess([], 0, "Available models\n  grok-4-fast - Fast\n  - grok-4-reasoning - Deep\n")
        with patch("catalog.subprocess.run", return_value=answer):
            self.assertEqual(listed("grok"), ["grok-4-fast", "grok-4-reasoning"])
        signed_out = subprocess.CompletedProcess([], 0, "You are not authenticated.\n  * grok-4.6\n")
        with patch("catalog.subprocess.run", return_value=signed_out), self.assertRaisesRegex(ValueError, "sign in"):
            listed("grok")
        codex = {"models": [{"slug": "gpt-hidden", "visibility": "hide"},
                            {"slug": "gpt-6-sol", "visibility": "list"}]}
        answer = subprocess.CompletedProcess([], 0, json.dumps(codex))
        with patch("catalog.subprocess.run", return_value=answer):
            self.assertEqual(listed("codex"), ["gpt-6-sol"])
        prompt = "extract this; $example"
        for host in ("claude", "cursor", "grok", "gemini"):
            with self.subTest(host=host), patch("routing.binary", return_value="cli"), patch("routing.subprocess.run") as run:
                route(["task", "--engine", host, "--models", "m1", "m2", "m3", prompt])
                cmd = run.call_args.args[0]
                self.assertEqual(cmd[:3], ["cli", "--model", "m1"])
                self.assertIn(prompt, cmd[-1])
        for host, command in ACP.items():
            with self.subTest(host=host), patch("routing.Session") as session:
                agent = session.return_value
                agent.ids = ["claude-haiku-6", "claude-opus-6"]
                agent.labels = {m: m for m in agent.ids}
                route(["task", "--engine", host, "extract"])
                session.assert_called_once_with(command)
                agent.turn.assert_called_once_with("extract", "claude-haiku-6")
                agent.close.assert_called_once()

    def test_protocol_exchange(self):
        server = """
import sys, json
def send(msg): print(json.dumps(dict(jsonrpc='2.0', **msg)), flush=True)
def options(v):
    return [{'id':'choice','category':'model','type':'select','currentValue':v,
             'options':[{'group':'test','options':[{'value':'gpt-6-sol','name':'Sol'},{'value':'gpt-6-luna','name':'Luna'}]}]}]
for line in sys.stdin:
    m=json.loads(line)
    method=m['method']
    if method=='initialize': r={'protocolVersion':1}
    elif method=='session/new': r={'sessionId':'s','configOptions':options('gpt-6-sol')}
    elif method=='session/set_config_option':
        assert m['params']=={'sessionId':'s','configId':'choice','value':'gpt-6-luna'}
        r={'configOptions':options('gpt-6-luna')}
    elif method=='session/prompt':
        send({'method':'session/request_permission','id':99,'params':{'options':[]}})
        assert json.loads(sys.stdin.readline())['result']['outcome']=={'outcome':'cancelled'}
        send({'method':'session/update','params':{'sessionId':'s','update':{'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':'OK'}}}})
        r={'stopReason':'end_turn'}
    else: raise AssertionError(method)
    send({'id':m['id'],'result':r})
"""
        agent = Session([sys.executable, "-c", server])
        try:
            agent.start()
            with patch("sys.stdin.isatty", return_value=False), redirect_stdout(StringIO()) as out:
                agent.turn("summarize", "gpt-6-luna")
            self.assertEqual(out.getvalue().strip(), "OK")
            with self.assertRaises(ValueError):
                agent.turn("next", "missing-model")
        finally:
            agent.close()

    def test_project_installs(self):
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            fixture = project / "build.log"
            fixture.write_text("ERROR code=Q193\n")
            for host in HOSTS:
                skill = install(host, project)
                self.assertEqual(install(host, project), skill)
                self.assertTrue((skill / "SKILL.md").is_file())
                text = subprocess.check_output([sys.executable, str(skill / "scripts/focus.py"),
                                               str(fixture), "-q", "code"], text=True)
                self.assertEqual(text, fixture.read_text())
            foreign = install("cursor", project) / "SKILL.md"
            foreign.write_text("my local edits")
            with self.assertRaises(ValueError):
                install("cursor", project)
            self.assertEqual(foreign.read_text(), "my local edits")


if __name__ == "__main__":
    unittest.main()
