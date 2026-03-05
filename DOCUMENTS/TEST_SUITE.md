# TinyTruce Test Suite

This document describes the test suite for the TinyTruce project, focusing on simulation integrity, agent grounding, and API integration.

## Core Simulation Tests

### [test_scenario_integrity.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_scenario_integrity.py)
Audits all scenario JSON files in the `scenarios/` directory. It verifies:
-   **Asset Availability**: Ensures all linked agent profiles, behavior fragments, and grounding payloads exist on disk.
-   **JSON Validity**: Checks for syntax errors in scenario files.
-   **Global Registry**: Verifies that essential engine files like `tinytruce_sim.py` and the `Forensic_Intelligence_Atlas.md` are present.

### [test_identity_guardian.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_identity_guardian.py)
Verifies the memory compression logic in `tinytruce_sim.py`. It confirms that:
-   **Episodic Memory Pruning**: Memory is correctly sliced when the window size is exceeded.
-   **Identity Preservation**: The core system message (Agent Identity) is NEVER pruned during compression.
-   **Anchor Archiving**: Summaries of pruned memory are correctly moved to the `_episodic_anchors` list.

### [test_atlas_auditor.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_atlas_auditor.py)
Tests the `extract_agent_grounding` function for resilience. It ensures the engine can handle:
-   **Messy Headers**: Resilience against leading/trailing spaces and capitalization mismatches in the Atlas.
-   **Agent Aliases**: Correctly maps names like "Donald Trump" to Atlas sections like "DJT" using the internal alias map.

### [test_verbosity.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_verbosity.py)
Validates the dynamic verbosity scaling logic. It ensures agents use "Lean" responses for opening/closing turns and "Detailed" responses for the core simulation turns.

### [test_revenue_shield.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_revenue_shield.py)
Mathematically verifies the `CostManager` logic, ensuring billing calculations for Gemini 2.0/2.5 flash models are accurate to the sixth decimal point. It also tests fallback pricing for unknown models.

---

## Agent Behavior & Safety

### [test_loop_guardsman.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_loop_guardsman.py)
Verifies the infinite loop protection in the agent's action loop. It confirms that agents are forcibly stopped if they exceed the `MAX_ACTIONS_BEFORE_DONE` threshold without issuing a `DONE` action.

### [test_voice_fidelity.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_voice_fidelity.py)
Tests the "Linguistic Lock" and "Fragment Stacking" logic. It ensures that vocabulary priorities and syntax constraints are correctly injected into the agent's system prompt.

### [test_universal_fidelity.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_universal_fidelity.py)
A structural audit that iterates through EVERY fragment in `personas/fragments/` to ensure they meet the hardening schema (Linguistic Locks) and correctly inject their contents into the prompt.

---

## Interactive & API Tests

### [test_chat_logic.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_chat_logic.py)
Tests the interactive `tinytruce_chat.py` script.
-   **Nudge Triggers**: Verifies that tactical or personal keywords trigger Situation Room and Ontological Shock alerts.
-   **Command Handling**: Tests `/fragment` and `/clear` command execution.

### [test_situation_room.py](file:///c:/Antigravity%20projects/TinyTruce/tests/unit/test_situation_room.py)
Tests the `SituationRoomFaculty` (RSS War News integration).
-   **Quota Enforcement**: Ensures the strict **one-query-per-turn** limit is enforced.
-   **API Resilience**: Verifies graceful handling of connection failures and API errors.

---

## Running the Suite
To run all TinyTruce tests:
```bash
python -m pytest tests/unit/
```
