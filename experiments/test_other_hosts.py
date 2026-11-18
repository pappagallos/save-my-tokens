import json
from pathlib import PurePosixPath
import unittest

from other_hosts import OTHER_GUIDES, OTHER_NEED_MODELS, OTHER_PROFILE_HOSTS, other_hosts

try:
    import tomllib
except ImportError:
    tomllib = None

try:
    import yaml
except ImportError:
    yaml = None


MODELS = ["provider/light", "provider/standard", "provider/deep"]
ROLES = ("light", "standard", "deep")


class OtherHostProfilesTest(unittest.TestCase):
    def test_profiles_and_manual_guides_cover_the_supported_hosts(self):
        self.assertEqual(len(OTHER_GUIDES), 12)
        self.assertLessEqual(OTHER_PROFILE_HOSTS, OTHER_GUIDES.keys())
        for host in OTHER_GUIDES:
            with self.subTest(host=host):
                files = other_hosts(host, MODELS if host in OTHER_NEED_MODELS else None)
                self.assertEqual(bool(files), host in OTHER_PROFILE_HOSTS)
                for name in files:
                    self.assertFalse(PurePosixPath(name).is_absolute())
                    self.assertNotIn("..", PurePosixPath(name).parts)

    def test_explicit_model_validation(self):
        for host in OTHER_NEED_MODELS:
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    other_hosts(host)
                with self.assertRaises(ValueError):
                    other_hosts(host, ["light", "standard\nmodel: injected", "deep"])
        with self.assertRaises(ValueError):
            other_hosts("antigravity", MODELS)
        with self.assertRaises(ValueError):
            other_hosts("rovodev", MODELS)

    def test_kiro_worker_json_pins_each_model(self):
        files = other_hosts("kiro", MODELS)
        for role, model in zip(ROLES, MODELS):
            data = json.loads(files[f".kiro/agents/smt-{role}.json"])
            self.assertEqual(data["model"], model)
            self.assertEqual(data["name"], f"smt-{role}")
            self.assertEqual("write" in data["tools"], role == "standard")
        self.assertTrue(files[".kiro/steering/smt-workers.md"].startswith("---\ninclusion: always\n"))

    @unittest.skipUnless(tomllib, "requires Python 3.11 or later")
    def test_vibe_worker_toml_pins_each_model(self):
        files = other_hosts("vibe", MODELS)
        for role, model in zip(ROLES, MODELS):
            data = tomllib.loads(files[f".vibe/agents/smt-{role}.toml"])
            self.assertEqual(data["agent_type"], "subagent")
            self.assertEqual(data["active_model"], model)
            self.assertEqual("enabled_tools" in data, role != "standard")

    @unittest.skipUnless(yaml, "requires PyYAML to parse YAML frontmatter")
    def test_markdown_profiles_use_documented_locations_and_model_fields(self):
        expected = {
            "antigravity": (".agents/agents", ("flash", "inherit", "pro")),
            "omp": (".omp/agents", MODELS),
            "pi": (".pi/agents", MODELS),
            "qoder": (".qoder/agents", ("lite", "efficient", "performance")),
            "rovodev": (".rovodev/subagents", (None, None, None)),
            "trae": (".trae/agents", MODELS),
            "trae-cn": (".trae/agents", MODELS),
        }
        for host, (directory, model_ids) in expected.items():
            files = other_hosts(host, MODELS if host in OTHER_NEED_MODELS else None)
            for role, model in zip(ROLES, model_ids):
                with self.subTest(host=host, role=role):
                    profile = files[f"{directory}/smt-{role}.md"]
                    opening, frontmatter, prompt = profile.split("---\n", 2)
                    self.assertFalse(opening)
                    self.assertTrue(prompt.strip())
                    data = yaml.safe_load(frontmatter)
                    self.assertEqual(data["name"], f"smt-{role}")
                    self.assertEqual(data.get("model"), model)
                    self.assertTrue(data["description"])
                    if role != "standard":
                        self.assertTrue(data["tools"])
                    if host == "antigravity":
                        self.assertFalse(data["mainAgent"])
                        self.assertTrue(data["subagent"])
