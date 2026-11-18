"""Minimal ACP v1 client for an installed agent that advertises model selection."""
import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
from threading import Thread


class Session:
    def __init__(self, command):
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, encoding="utf-8")
        self.sequence = 0
        self.updates = Queue()
        self.option = None
        self.ids = []
        self.labels = {}
        self.session = None
        self.reader = Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.proc.stdout:
                self.updates.put(line)
        finally:
            self.updates.put(None)

    def send(self, message):
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        self.proc.stdin.flush()

    def configure(self, options):
        for opt in options:
            if opt["type"] == "select" and (opt.get("category") == "model" or opt["id"] == "model"):
                self.option = opt["id"]
                self.current = opt["currentValue"]
                self.labels = {v["value"]: v["name"] for group in opt["options"] for v in group.get("options", [group])}
                self.ids = list(self.labels)
                return

    def call(self, method, params, timeout=30):
        self.sequence += 1
        self.send({"id": self.sequence, "method": method, "params": params})
        while True:
            try:
                line = self.updates.get(timeout=timeout)
            except Empty:
                raise RuntimeError(f"agent did not answer {method} within {timeout}s") from None
            if line is None:
                raise RuntimeError(f"agent closed the connection during {method}")
            msg = json.loads(line)
            if "method" not in msg:
                if msg.get("id") != self.sequence:
                    raise RuntimeError("unexpected response ID from agent")
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error'].get('message')}")
                return msg["result"]
            if msg["method"] == "session/update":
                update = msg["params"]["update"]
                kind = update["sessionUpdate"]
                if kind == "agent_message_chunk" and update["content"]["type"] == "text":
                    print(update["content"]["text"], end="", flush=True)
                if kind == "config_option_update":
                    self.configure(update["configOptions"])
            elif "id" in msg:
                if msg["method"] == "session/request_permission":
                    outcome = {"outcome": "cancelled"}
                    if sys.stdin.isatty():
                        opts = [v for v in msg["params"]["options"] if v["kind"] == "allow_once"]
                        title = msg["params"]["toolCall"].get("title", "tool call")
                        if opts and input(f"\nAllow once: {title}? [y/N] ").lower() == "y":
                            outcome = {"outcome": "selected", "optionId": opts[0]["optionId"]}
                    self.send({"id": msg["id"], "result": {"outcome": outcome}})
                else:
                    self.send({"id": msg["id"], "error": {"code": -32601, "message": "Unsupported method"}})

    def start(self):
        init = self.call("initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        if init["protocolVersion"] != 1:
            raise RuntimeError("agent does not negotiate ACP v1")
        data = self.call("session/new", {"cwd": str(Path.cwd()), "mcpServers": []})
        self.session = data["sessionId"]
        self.configure(data.get("configOptions", []))
        if self.option is None and data.get("models"):
            models = data["models"]
            self.labels = {m["modelId"]: m["name"] for m in models["availableModels"]}
            self.ids = list(self.labels)
            self.current = models["currentModelId"]
        if not self.ids:
            raise ValueError("this agent exposes no model picker over ACP; use an explicitly chosen CLI engine")

    def turn(self, prompt, model):
        if model not in self.ids:
            raise ValueError(f"{model} is not in the agent's current model list")
        if model != self.current:
            if self.option:
                result = self.call("session/set_config_option",
                                   {"sessionId": self.session, "configId": self.option, "value": model})
                self.configure(result["configOptions"])
                if self.current != model:
                    raise RuntimeError("agent did not confirm the selected model")
            else:
                self.call("session/set_model", {"sessionId": self.session, "modelId": model})
                self.current = model
        result = self.call("session/prompt", {"sessionId": self.session,
                           "prompt": [{"type": "text", "text": prompt}]}, timeout=300)
        print(flush=True)
        if result["stopReason"] != "end_turn":
            raise RuntimeError(f"agent stopped: {result['stopReason']}")

    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.reader.join(timeout=2)
        self.proc.stdout.close()
