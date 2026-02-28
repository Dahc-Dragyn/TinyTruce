# TinyTruce: Scenario Blueprint Guide (V1.0)

Scenarios in TinyTruce are not just "chat prompts"—they are multi-layered geopolitical machines designed to force negotiation.

---

## 🛠️ Scenario Architecture (.json)

### 1. The Initial Broadcast (Breaking News)
- **Objective**: Set the stakes immediately.
- **Forensic Anchor**: Reference current events (2025-2026) using high-fidelity terminology (e.g., "Ultralight Failure", "Context-Cutter").

### 2. Forensic Grounding (`grounding_payload`)
Lists of relative paths to factual data. 
- **Rule**: Map specific logs to specific scenarios. Avoid global factual dumps to minimize token noise and context drift.

### 3. The Intervention Protocol (The Peace Bomb)
An invisible strategic auditor monitors the chat. If it detects a stalemate, it injects a "Peace Bomb"—a semantic nudge that forces agents to pivot from philosophy to kinetic compromise.

### 4. Dynamic Injects (Procedural Crisis)
Probability-based events (e.g., "25% chance of a localized power grid failure"). These keep the simulation "alive" and prevent agents from settling into comfortable, repetitive loops.

---

## 🔄 The Simulation Loop
1.  **Initialization**: `AssetManager` validates the scenario JSON and grounding files.
2.  **Turn Flow**: Agents alternate `THINK` -> `TALK` -> `DONE`.
3.  **Narrator Window**: "Salty British Documentarian" interrupts every 5 turns to recalibrate the vibe.
4.  **Strategic Audit**: At completion, the `StrategicAuditor` generates a de-escalation scorecard (`tinytruce_briefing.md`).
5.  **Final Recap**: "The Bartender" generates the forensic roast (`tinytruce_roast.md`).

---

## 5. Testing & Quality Assurance
Every new scenario should be validated to ensure agents maintain their idiolect under the scenario's specific pressures.
- **Baseline Check**: Run `python -m pytest tests/unit/test_validation.py -k "<scenario_agent>"` to verify the agent sounds correct.
- **Regression Suite**: Run the Zero-Cost scripts (Loop-Guardsman, Identity Guardian) to ensure the scenario config doesn't trigger engine-level failures.
- **Performance Audit**: Check `DOCUMENTS/tinytruce_billing_ledger.md` after a run to verify the scenario isn't unexpectedly expensive.

---

## 📐 Design Patterns
- **High-Stakes Bilateral**: 2 agents, 10 turns. Ideal for deep philosophical schisms.
- **Multilateral Summit**: 3-5 agents, 15 turns. Requires a narrator to manage noise.
- **Monologue/SOTU**: 1 agent, 6 turns. Focused on linear delivery and catchphrase fidelity.

---

*“A good scenario doesn't ask for peace; it makes war too expensive to continue.”*
