---
name: web-dashboard-audit
description: Use when auditing or rebuilding a web dashboard.
version: 1.0.0
metadata:
  hermes:
    tags: [dashboard, browser, qa, ui, reverse-engineering]
---

# Web Dashboard Audit and Rebuild

Use this skill when auditing an existing dashboard, comparing navigation/features, or rebuilding a replacement UI.

## Workflow

1. Define read-only scope, target URL, protected processes, and authentication authorization. Never restart or modify the reference service during audit.
2. Prefer managed browser tools. If unavailable, use installed Chromium/Firefox through Playwright headless. Capture URL, title, visible text, links, buttons, forms, screenshot, and console errors.
3. Use only explicitly authorized credentials. Never brute-force. After a failed authorized login, stop live auth attempts and use source/build route inspection to fill gaps.
4. Build a feature matrix: navigation, providers/accounts, models, fallback/combos, usage, logs/activity, settings, auth, integrations, tunnel/network surfaces, and loading/empty/error states.
5. Separate behavior from styling. Extract requirements without cloning reference palette, layout, or branding unless explicitly requested.
6. Rebuild around the user's actual scope. Prefer compact sections such as Overview, Providers, Routing, and Access. Keep secrets, tokens, prompts, and identifiers out of responses.
7. Validate locally: build, serve, check health/API routes, inspect DOM, exercise navigation/forms, test narrow viewport, and check console errors.
8. Persist objective, scope, feature matrix, limitations, decisions, verified results, and next step in the concrete Obsidian vault.

## CLI/UI legibility

Prefer simple ASCII separators and fixed columns. Avoid emoji, box-drawing, centered blocks, and wide Unicode in alignment-sensitive terminal regions. If Unicode is necessary, calculate terminal display width rather than byte length and test normal and narrow TTYs. Keep action lists short and descriptions concise.

## Browser fallback evidence

Report browser/runtime, URL/final redirect, title, visible text, controls, screenshots, console status, authentication limits, and source/build artifacts used to fill gaps. Do not claim pixel-level audit when authentication or browser setup prevented it.

## Rebuild principles

- Extract feature requirements, not visual identity.
- Default operational dashboards to local-only binding.
- Use responsive grids and touch-sized controls; prevent horizontal overflow.
- Redact API keys, tokens, cookies, raw prompts, and account emails.
