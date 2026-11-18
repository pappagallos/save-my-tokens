---
name: route-task
description: Use when asked to perform work with automatic model selection by request or to continue a routed workflow.
---

Classify the user's requested deliverable. Use a lightweight worker for clear extraction, translation and classification, a focused worker for screenshots or a change confined to one file or function, a general coding worker for implementation, and a deep reasoning worker for ambiguous root causes and cross-service design. For a bare continuation keep the previous task tier. Honor an explicit model. If the Auto Workers companion is installed and enabled, follow its standing opt-in and available-model rules in ordinary conversations. Use an available native worker with that model when delegation is requested and permitted. Give it the relevant context, collect its result, and report the actual worker. If the current model fits, do the work directly. If switching is unavailable, say so. The host controls the active chat's model.

For a human who wants the main Codex model to switch at each message, the installed terminal launcher provides `save-my-tokens chat`. It resumes the same thread with the selected model. Avoid launching nested CLI sessions to evade the current chat's permissions.

In the terminal, `save-my-tokens models --engine codex` shows the current account catalog and all four routes. The CLI resolves the selected family for each request.
