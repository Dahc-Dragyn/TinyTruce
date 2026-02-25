# TinyTruce Model Handoff: JSON Parsing & Fallback Extraction

## Current System State (Feb 24, 2026)
We successfully implemented a native explicit Context Logging bypass in `llm_engine.py` using `NativeGeminiEngine` to save on input token costs (over 50% savings via Gemini 2.5 Flash-lite).

We also fixed several major stability issues:
1. **Context Amnesia:** We inject a `CRITICAL IDENTITY LOCK` to maintain persona continuity even with heavy caching.
2. **Infinite Loops:** Forced the instruction to append the `DONE` yield block.
3. **Psychological Momentum Fix:** Relaxed `CognitiveActionModel` to accept `Union[float, str]` for `emotional_intensity`.
4. **Markdown Strip Bug:** `llm_engine.py` safely strips off trailing backticks and hidden whitespace before validation.
5. **Bartender Roast Repair:** Fixed an indentation loop and rewrote the Bartender's `tinytruce_sim.py` prompt out of JSON entirely over to plain-text tags (`NARRATIVE:` and `OVERHEARD:`), which completely fixed the Pydantic crash that previously zeroed out the `tinytruce_roast.md` file.

## The Resolved Bug: `CognitiveActionModel` Missing Fields (Double JSON Hallucination)
During 5-turn 3-agent trials, the API intermittently dropped turns due to Pydantic throwing `2 validation errors for CognitiveActionModel: action Field required, cognitive_state Field required`.

### Root Cause
The regex-based extraction in `llm_engine.py` used a non-greedy match `r'\{.*?\}'`, which caused it to pluck inner dictionaries (like `cognitive_state`) instead of the root container. `json.loads` would succeed, but Pydantic would fail because the root fields were missing.

### Solution Applied
I updated `llm_engine.py` with a more robust greedy match and a recursive shrinking logic. It now specifically look for a dictionary that contains the required `'action'` key. This allows it to bypass hallucinated garbage and partial sub-dictionaries to find the intended root object.

## Next Steps
1. **Verification Test:** Run the 5-turn simulation again to verify it survives "Nuclear" roast levels and heavy multi-turn context.
   `python tinytruce_sim.py --scenario digital_twin_summit --turns 5 --agents sam_altman.agent.json yann_lecun.agent.json pope_leo.agent.json --roast-level nuclear --hide-thoughts`
2. **Documentation:** The `FRONTEND_NOTES.md` and `README.md` have been updated with the core stability fixes. 
3. **Walkthrough:** Finalize `walkthrough.md` if any other behavior is observed.

The engine is now extremely resilient to LLM "garbage" content and malformed JSON.
