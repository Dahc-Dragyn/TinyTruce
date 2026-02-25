# TinyTruce: Run Credits Plan

## Goal
The goal of this plan is to evaluate the monetization potential of TinyTruce and propose a technical framework for transitioning from a "pure testing" phase to a "pay-per-run" model.

## Strategic Assessment: "Will people pay?"
**Yes.** Based on a forensic analysis of the project's assets (e.g., the Xi Jinping persona), TinyTruce offers a "forensic-grade" simulation that exceeds standard LLM outputs. 

### Key Value Drivers
- **Deep Ingestion Moat**: The personas are grounded in unscripted cognitive routing analysis (e.g., Chengyu linguistic walls, DARVO mechanics). This isn't just a "bot"; it's an intelligence-grade asset.
- **Analytical KPI Suite**: The `Resolve Scorecard`, `Attribution Log`, and `Stability Index` provide professional-level insights for defense, diplomacy, and trade analysts.
- **Low Operational Cost**: Using `gemini-2.5-flash-lite-preview` with explicit context caching keeps the marginal cost per run low (likely <$0.50 for a standard run), allowing for competitive pricing.

## Proposed Changes

### [Engine Layer]
#### [MODIFY] [llm_engine.py](file:///c:/Antigravity%20projects/TinyTruce/tinytroupe/llm_engine.py)
Iterate on `NativeGeminiEngine` to ensure `cached_content` is always utilized for Layer 0 dossiers, minimizing the "testing bill" for the developer while maximizing value for the user.

### [Simulation Controller]
#### [MODIFY] [tinytruce_sim.py](file:///c:/Antigravity%20projects/TinyTruce/tinytruce_sim.py)
[NEW] Implement a "Simulation Credit" check.
- Add a `--credit-key` argument or environment variable check.
- Integrate a pre-run validation that ensures the user has "Simulation Seconds" or "Run Credits" available.

## Verification Plan

### Automated Tests
- Run `python tinytruce_sim.py --check-credits` to verify the new credit validation logic.
- Execute a cached run and verify in the logs that token counts remain within the "Lite" budget.

### Manual Verification
- Execute the "Neural Sovereignty" scenario (10 turns) and verify that the "Attribution Log" correctly identifies maneuvers with >90% confidence, justifying its status as a premium product.
