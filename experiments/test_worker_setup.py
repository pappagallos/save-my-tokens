"""Exercise the actual installation paths without external accounts or API calls."""
import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from install import HOSTS, install
from native_profiles import NATIVE_HOSTS, profiles
from other_hosts import OTHER_NEED_MODELS, OTHER_PROFILE_HOSTS, other_hosts
from worker_setup import setup


class WorkerInstallation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = ["vendor/mini", "vendor/standard", "vendor/deep"]

    def test_every_host_through_the_installer(self):
        for host in HOSTS:
            with self.subTest(host=host):
                project = self.root / host
                project.mkdir()
                cli = [sys.executable, str(ROOT / "install.py"), "--platform", host, "--project",
                       str(project), "--auto-workers"]
                needs_ids = (NATIVE_HOSTS - {"claude"}) | OTHER_NEED_MODELS
                models = self.models if host in needs_ids else None
                if models:
                    cli += ["--worker-models", *models]
                for _ in range(2):
                    result = subprocess.run(cli, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                if host in NATIVE_HOSTS | OTHER_PROFILE_HOSTS:
                    files = profiles(host, models) if host in NATIVE_HOSTS else other_hosts(host, models)
                    for rel, expected in files.items():
                        self.assertEqual((project / rel).read_text(), expected)
                elif host == "grok":
                    self.assertIn("explore", (project/".grok/rules/save-my-tokens-workers.md").read_text())
                else:
                    self.assertTrue("Host action required" in result.stdout or "native plugin switch" in result.stdout)

    def test_refresh_preserves_existing_work_and_rules(self):
        p = self.root
        (p/"GEMINI.md").write_bytes(b"# My project\r\n")
        skill = install("gemini", p)
        with patch("worker_setup.discover", return_value=self.models) as discover:
            setup("gemini", p, skill)
            discover.assert_called_once_with("gemini", p.resolve())
        setup("gemini", p, skill, ["next-light", "next-standard", "next-deep"])
        shared = (p/"GEMINI.md").read_bytes()
        self.assertTrue(shared.startswith(b"# My project\r\n"))
        self.assertEqual(shared.count(b"<!-- save-my-tokens:"), 1)
        worker = p/".gemini/agents/smt-standard.md"
        self.assertIn("next-standard", worker.read_text())
        worker.write_text("my replacement")
        before = (p/".gemini/agents/smt-light.md").read_text()
        with self.assertRaises(ValueError):
            setup("gemini", p, skill, self.models)
        self.assertEqual(before, (p/".gemini/agents/smt-light.md").read_text())
        self.assertEqual(worker.read_text(), "my replacement")

    @unittest.skipUnless(importlib.util.find_spec("tomllib") or importlib.util.find_spec("tomli"),
                         "Grok personal settings need a TOML parser")
    def test_native_personal_settings(self):
        import os
        home = self.root/"home"
        project = self.root/"project"
        home.mkdir()
        project.mkdir()
        grok = home/".grok"
        grok.mkdir()
        g = grok/"config.toml"
        g.write_text('[models]\ndefault = "mine"\n[subagents.models]\nexplore = "prev"  # note\ncustom = "keep"\n[cli]\nauto_update = false\n')
        d = home/".config/devin/config.json"
        d.parent.mkdir(parents=True)
        d.write_text('{"agent":{"model":"previous","other":1},"retain":true}')
        with patch("worker_setup.Path.home", return_value=home), patch.dict(os.environ, {"GROK_HOME":str(grok)}):
            gs = install("grok", project)
            ds = install("devin", project)
            for _ in range(2):
                setup("grok", project, gs, self.models, True)
                setup("devin", project, ds, user_settings=True)
        self.assertIn('explore = "vendor/mini"  # note', g.read_text())
        self.assertIn('custom = "keep"', g.read_text())
        self.assertEqual(g.read_text().count("general-purpose"), 1)
        self.assertEqual(json.loads(d.read_text()), {"agent":{"model":"adaptive","other":1},"retain":True})

    @unittest.skipUnless(importlib.util.find_spec("tomllib") or importlib.util.find_spec("tomli"),
                         "Grok personal settings need a TOML parser")
    def test_grok_profile_collision_leaves_personal_settings_untouched(self):
        import os
        config_home = self.root / "grok-home"
        config_home.mkdir()
        cfg = config_home / "config.toml"
        cfg.write_text('[models]\ndefault = "mine"\n')
        project = self.root / "project"
        project.mkdir()
        skill = install("grok", project)
        rule = project / ".grok/rules/save-my-tokens-workers.md"
        rule.parent.mkdir()
        rule.write_text("custom")
        with patch.dict(os.environ, {"GROK_HOME": str(config_home)}), self.assertRaises(ValueError):
            setup("grok", project, skill, self.models, True)
        self.assertEqual(cfg.read_text(), '[models]\ndefault = "mine"\n')

    def test_symlink_is_not_followed(self):
        out = self.root/"outside"
        out.mkdir()
        p = self.root/"project"
        p.mkdir()
        skill = install("claude", p)
        (p/".claude/agents").symlink_to(out, target_is_directory=True)
        with self.assertRaises(ValueError):
            setup("claude", p, skill)
        self.assertEqual(list(out.iterdir()), [])
