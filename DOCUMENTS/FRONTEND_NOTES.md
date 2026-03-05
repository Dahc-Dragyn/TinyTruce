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
| **Fragments** | `list[string]` | Behavioral overlays. Supports **Behavioral Stacking** via comma-separation. Each fragment now contains a `redlines` array for negative constraints. | Multi-select dropdown. |

| **Roast Level** | `enum` | Intensity of the Bartender recap (`mild`, `spicy`, `nuclear`). | Radio buttons or slider. |
| **Eco Mode** | `boolean` | Activates **Input Slicing** and forces high-efficiency Flash-Lite models. | Toggle switch ("Eco Mode"). |
| **UX Mode** | `boolean` | Whether to display (`false`) or hide (`true`) internal agent thoughts. | Checkbox ("Hide Internal Thoughts"). |
| **Verbosity** | `enum` | Response length control (`lean`, `detailed`, `monologue`, `dynamic`). | Dropdown selection (Recommended: `dynamic`). |
| **Session ID** | `string` | Unique identifier for run isolation and output routing. | Auto-generated UUID or custom string. |
| **Interactive Mode** | `script` | `tinytruce_chat.py` provides a 1-on-1 interrogation interface. | Terminal/Console Interface. |

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
- `persona.redlines`: Hard boundaries or trigger points for the base agent (Layer 0).
- **Forensic Grounding (Layer 2)**: All 27 fragments in `../personas/fragments/` are now grounded in forensic anchors (V2.1 Rollout). Each fragment uses strictly derived `redlines` to enforce situational tactical constraints.
### Geopolitical Chronicler & Daily Grounding
- **The Chronicler**: A standalone agent system (`scripts/chronicler_update.py`) that acts as a "Forensic Scribe".
- **Workflow**: 
    1. Harvests news via `SituationRoomFaculty` (targeting Top 5 scenarios: AI Sovereignty, Petrodollar, Domestic, etc.).
    2. Synthesizes a structured `daily-intelligence.2026.txt`.
    3. Commits to the shared World State.
- **Grounding**: All agents in `tinytruce_sim.py` automatically load this daily intelligence. This ensures a "Stable Narrative Baseline" and prevents token-heavy redundant API calls.
- **Cost**: Optimized to ~$0.02 per global update for 5 targeted scenario-based queries.
- **Severity**: Uses a 1-5 forensic severity scale for high-signal alerts.
- **The Situation Room**: Agents can now perform `SEARCH_NEWS` (to retrieve theater grounding) and `GET_ALERTS` (to retrieve high-signal breaking news).
  - *Action:* `action: {"type": "SEARCH_NEWS", "content": "Query String", "target": "everyone"}`

> [!IMPORTANT]
> **Manual World State Refresh**: While the Chronicler system is server-side, it must be triggered manually via `python scripts/chronicler_update.py` (or a scheduled cron job) to refresh the shared `daily-intelligence.2026.txt` world state. Frontend developers should ensure this "Dawn Command" has been executed after any major deployment or daily cycle.
- **The `thought` Field**: High-fidelity agents now use a dedicated `thought` field in the `CognitiveActionModel` to consolidate reasoning within the same JSON block as their response.
  - *JSON Structure:* `{"action": {...}, "cognitive_state": {...}, "thought": "Reasoning string..."}`
- **Handling Redlines**: The `persona.redlines` array should be visualized as "Tactical Bounds" or "Negotiation Constraints" in the UI. When multiple fragments are chained, the engine **aggregates** these arrays. Frontends should treat these as negative constraints—behavior the agent *must not* exhibit.

### Interactive Commands (`tinytruce_chat.py`)
Users can interact with agents via terminal commands in the chat script:
- `/fragment <name>`: Ingest a new behavior fragment mid-session.
- `/clear`: Prunes agent memory (reset context).
- `/bye`: Safely terminates the session and cleans up caches.

---

## 2. Visual Asset Registry (South Park Library)
The `../images/` directory contains high-resolution character portraits for all primary agents. These assets are technically optimized for UI integration (flat colors, vibrant solid backgrounds for easy transparency removal/chroma-keying).

| Agent Name | South Park Outfit | BG Color | Unique Defining Feature |
| :--- | :--- | :--- | :--- |
| **Vladimir Putin** | Dark suit with a small "Z" or eagle pin. | Vibrant Red | Cold, squinting eyes; slightly smirked mouth. |
| **Xi Jinping** | Traditional dark Mao-style suit. | Bright Yellow | Rounded face; calm, stoic expression. |
| **Donald Trump** | Signature blue suit, white shirt, and long red tie. | Electric Blue | Iconic swooped blonde hair; "O" shaped mouth. |
| **Narendra Modi** | White kurta with a saffron-colored vest. | Neon Orange | Flowing white beard; rimless glasses. |
| **Emmanuel Macron** | Slim-fit navy blue presidential suit. | Cobalt Blue | Sharp, youthful features; slightly messy "French" hair. |
| **Keir Starmer** | Plain dark charcoal legalistic suit. | Magenta | Neat, graying hair; very large, thick-rimmed glasses. |
| **Benjamin Netanyahu** | Formal blue suit with a light blue tie. | Cyan | Deep-set eyes; receding gray hairline. |
| **Mohammed bin Salman** | Traditional white Thobe and red-and-white Ghutra. | Lime Green | Thick black beard; intense, focused gaze. |
| **Ali Khamenei** | Dark cloak and traditional black turban. | Emerald Green | Long white beard; thin, wire-framed glasses. |
| **Lula da Silva** | Casual suit jacket with an open-neck shirt. | Bright Yellow | Grey beard; missing pinky finger on the left hand. |
| **Volodymyr Zelensky** | Tactical olive green crew-neck sweatshirt. | Neon Green | Short brown beard; tired but defiant eyes. |
| **Antonio Guterres** | Grey suit with a slightly loose, drab tie. | Sky Blue | Worried eyebrows; "Cassandra Complex" frown. |
| **Ursula von der Leyen** | Brightly colored blazer (e.g., magenta). | Neon Purple | Distinctive blonde "hardened" bob hairstyle. |
| **Sheikh Mohammed** | Modern Qatari Thobe and white Ghutra. | Desert Gold | Clean-shaven; holding a futuristic smartphone. |
| **Pope Leo XIV** | Full white papal cassock and zucchetto. | Royal Purple | Gentle, "humanist" smile; holding a rosary. |
| **Rishi Sunak** | Very slim-fit suit; "Post-PM" tech-casual vibe. | Electric Blue | Large ears; holding a small "Peloton" water bottle. |
| **Elon Reeve Musk** | Dark grey T-shirt or "DOGE" flight jacket. | Cyber Purple | Slight stutter-step mouth pose; holding a Mars rocket. |
| **Sam Altman** | Grey hoodie and dark jeans. | Acid Green | Large, "optimist" eyes; slightly messy hair. |
| **Yann LeCun** | Casual sweater over a collared shirt. | Bright Orange | Academic glasses; holding a "JEPA" blueprint. |
| **Bill Gates** | V-neck sweater over a button-down shirt. | Soft Blue | Round glasses; "Technocratic Paternalist" smirk. |
| **Dr. Elara Vance** | High-tech lab coat with quantum patterns. | Neon Pink | Holding a glowing "Junko Network" data cube. |
| **Kim Jong Un** | Black double-breasted Mao suit. | Blood Red | Iconic "high-top" fade haircut; smiling broadly. |
| **Nicolas Maduro** | Red track jacket or prisoner jumpsuit. | Safety Orange | Thick black mustache; "Martyrdom" expression. |
| **Assimi Goita** | Full desert camouflage military fatigues. | Sandy Brown | Green beret; intense, paranoid side-eye. |
| **Abiy Ahmed** | Suit with an Ethiopian flag pin. | Yellow-Green | Short-cropped hair; holding a "GERD" dam model. |
| **Tarique Rahman** | Formal business suit. | Teal | Polished appearance; "Revanchist" glare. |
| **Prabowo Subianto** | Traditional Indonesian Safari suit. | Burnt Orange | "Strongman" posture; rounded features. |
| **Min Aung Hlaing** | Traditional Burmese military uniform. | Olive Drab | Military cap; "Besiegement" frown. |
| **The Bartender** | White apron over a stained t-shirt. | Dirty Brown | Red, "barfly" nose; holding a dirty towel. |

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

## 4. Output Artifacts (Isolated by Session)
All outputs are now written to `DOCUMENTS/runs/{session_id}/` to support multi-tenant frontends.

### A. The Strategic Briefing (`tinytruce_briefing.md`)
1.  **Executive Summary:** High-level overview.
2.  **Resolve Scorecard:** Radar/Bar graph data (Stakes, Aggression, Flexibility).
3.  **Stability Index:** Overall truce quality (GREEN, YELLOW, RED).
4.  **Redline Breach Report:** Details on compromises to core beliefs.

### C. The Billing Record (`tinytruce_billing_ledger.md`)
- **Format:** Markdown table with per-scenario breakdown.
- **Fields:** Timestamp, Scenario, Input Tokens, Output Tokens, Cached Tokens, Total Cost (USD).
- **Frontend Utility:** Can be parsed to display a "Simulation Budget" or "Session Cost" dashboard.

---

## 5. Billing & Pricing Logic
The frontend can expose pricing configuration via `DOCUMENTS/Gemini_Pricing.json`.
- **Pricing Unit:** Most models are billed per 1M tokens.
- **Eco Mode Impact:** When active, the engine slices history by 66% before sending it to the LLM, drastically reducing input costs in turns 5-10.
- **Elastic Context Window:** The engine automatically summarizes and prunes conversational history into **Episodic Anchors** when turns exceed 8, ensuring input token costs remain stabilized even in long simulations.
- **Cached Tokens:** Are billed at ~25% of the standard input rate.

---

## 6. UI/UX: The Dual-Panel Concept
- **Story Mode:** Clean, minimalist chat bubbles focusing on the diplomatic exchange.
- **God Mode / Debug View:** Side-panel exposing `💭 THINKING` steps and `[PSYCHOLOGICAL MOMENTUM]` bars.
