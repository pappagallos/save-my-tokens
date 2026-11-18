---
name: assign-worker
description: Delegate independent subtasks to Codex workers on ordinary requests. Choose an available model per worker and keep the main conversation on the selected model.
---

# Assign a worker

In the main conversation, apply this instruction on each request when this skill is enabled and the user has opted into automatic delegation. Respect current user instructions, project rules and host restrictions. Workers finish their own assignment without spawning more workers.

Handle short answers and work on the critical path directly. When a separate investigation, implementation or check can run independently and its result will materially advance the request, delegate it with the host's native spawn tool. For example, if a request asks for two independent investigations, assign one to a worker before starting the other yourself. Keep the main agent responsible for user interaction, dependent decisions, integration and the final response. Avoid duplicating work and sending a long conversation to a worker for a short task.

Choose a model when starting each new worker. Use only models allowed by the native spawn tool in this conversation and roles that permit a model override. Among eligible models in a family, prefer the newest available version. The following choices are this plugin's routing policy.

| Work assigned | Preferred family | Alternatives in order |
| --- | --- | --- |
| Extract a few named facts from given material | Luna | Terra, Sol |
| Trace a file path or diagnose a bounded local issue | Terra | Sol |
| Implement a change across related files | Sol | Terra |
| Analyze a difficult design trade-off or a subtle correctness issue | Astra | Sol |

If an appropriate native role fixes its own model, use that role's model. If none of the listed families is available, use the host's default worker. If delegation is unavailable, do the work in the main conversation. Do not launch a separate CLI to simulate a native worker.

When selecting a model explicitly, create a fresh worker with no history fork if the host requires it. Send the relevant paths, objective, constraints and expected evidence. Give concurrent writers disjoint file ownership. Continue independent work while the worker runs. Check its result before relying on it. Report the actual model only when confirmed by the host. For a usage comparison, include every child as well as the parent and distinguish cached input from total input. Starting a worker costs tokens and requires a separate call. Never infer token savings from the family name or claim that internal reasoning steps were rerouted.
