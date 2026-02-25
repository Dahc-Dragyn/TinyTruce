# TinyTruce: Frontend Integration Data Sheet (V2.1)

This document serves as the canonical reference for frontend developers building an interface for the **TinyTruce Geopolitical Conflict Lab**. It outlines the configurable inputs, data structures for agents and scenarios, and the generated output artifacts.

---

## 1. Configurable Inputs (Simulation Parameters)
The frontend must provide a way for the user to select or configure the following parameters before launching a simulation:

| Parameter | Type | Description | Frontend Control Suggestion |
| :--- | :--- | :--- | :--- |
| **Scenario** | `string` | The geopolitical event to simulate (loaded from `../scenarios/*.json`). | Dropdown menu featuring scenario names. |
| **Turns** | `integer` | Duration of the simulation. Baseline recommendation is 5-10. | Number input or slider (Range: 1-20). |
| **Model Selection** | `string` | Primary engine. **Gemini 2.0 Flash-Lite** is the default and runs natively via `NativeGeminiEngine`. | Selector (Defaults to Gemini 2.0). |
| **Context Caching** | `boolean` | Activates **Explicit Context Caching** via the native engine. | Toggle switch (Reduces per-turn billing by 50%+). |
| **Agents** | `list[string]` | The base participants (loaded from `../personas/agents/*.agent.json`). | Multi-select dropdown. |
| **Fragments** | `list[string]` | Behavioral overlays (from `../personas/fragments/*.fragment.json`). | Dropdown next to each selected agent. |
| **Narrator Mode** | `enum` | Commentary style (`off`, `salty`, `neutral`). | Radio buttons or toggle switch. |
| **Roast Level** | `enum` | Intensity of the Bartender recap (`mild`, `spicy`, `nuclear`). | Radio buttons or slider. |
| **UX Mode** | `boolean` | Whether to display (`false`) or hide (`true`) internal agent thoughts. | Checkbox ("Hide Internal Thoughts"). |

---

> All JSON assets are validated against Pydantic schemas in `tinytroupe/asset_manager.py`. The system uses **Permissive Validation** (`extra='ignore'`), meaning it accepts unknown keys but will **FAIL-FAST** if known keys have the wrong data type (e.g. `persona` being a string instead of a dictionary).

### Scenarios (`../scenarios/*.json`)
- `world_name`: Location of the summit.
- `initial_broadcast`: The inciting incident text (Breaking News).
- `intervention`: The "Peace Bomb" de-escalation nudge.
- `dynamic_injects`: Array of procedural mid-simulation crisis events.
- `grounding_files`: Array of relative paths to factual grounding data.

### Personas (Agents) (`../personas/agents/*.agent.json`)
- `persona.name` / `persona.full_name`: Agent identity.
- `persona.occupation.title`: The agent's formal role.
- `persona.personality.traits`: Descriptive trait strings.
- `persona.redlines`: Hard boundaries or trigger points for the agent.

---

## 3. Realtime Events Stream (Engine-to-UI)
The frontend captures the standard output (or log stream) to render:
- **Phases:** "Opening Statements...", "Identity Reinforcement...", etc.
- **Agent Action:** Dialogue (`💬 TALK`) and internal thoughts (`💭 THINKING`).
- **Mood Bars:** Emotional intensity tracking (e.g., `[PASSIVE]`, `[TENSE]`, `[VOLATILE]`).
  - *Frontend Parsing Note:* The `emotional_intensity` field is now **Optional** and handled via a `Union[float, str]` to withstand SDK-induced type-casting. If the LLM omits the field, the engine defaults to a decay model instead of zeroing out.
  - *Markdown Parsing Note:* Be sure to strip all trailing spaces/newlines from raw SDK outputs *before* performing `.endswith("\`\`\`")` checks, or else extra trailing ticks will stay attached and cause `Invalid JSON: trailing characters` errors.
- **Cache Activation:** Logs like `Applied Context Cache` confirm per-turn cost savings.
- **Fail-Fast Validation:** Diagnostics like `[FATAL VALIDATION ERROR]` indicate a schema breach in a JSON asset.
- **Zero-Cost Diagnostics:** A standalone `verify_cache.py` script is provided to audit backend Gemini Context Caches via the Management API without triggering inference billing.

---

## 4. Output Artifacts

### A. The Strategic Briefing (`tinytruce_briefing.md`)
1.  **Executive Summary:** High-level overview.
2.  **Resolve Scorecard:** Radar/Bar graph data (Stakes, Aggression, Flexibility).
3.  **Stability Index:** Overall truce quality (GREEN, YELLOW, RED).
4.  **Redline Breach Report:** Details on compromises to core beliefs.

### B. The Bartender Roast (`tinytruce_roast.md`)
- **Main Narrative:** Clinical, detached comedic breakdown using V2 comediac logic.
- **Punchlines:** High-intensity snipes on diplomatic failures.

---

## 5. UI/UX: The Dual-Panel Concept
- **Story Mode:** Clean, minimalist chat bubbles focusing on the diplomatic exchange.
- **God Mode / Debug View:** Side-panel exposing `💭 THINKING` steps and `[PSYCHOLOGICAL MOMENTUM]` bars.
