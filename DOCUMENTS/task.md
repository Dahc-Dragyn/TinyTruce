# Task Checklist: Forensic Jurist Integration

- [x] Implement "The Forensic Jurist" (Layer 0 Auditor) <!-- id: 77 -->
    - [x] Create Jurist deep profile `wjp_auditor.txt` <!-- id: 78 -->
    - [x] Fix and improve `the_forensic_jurist.agent.json` (persona key fix) <!-- id: 79 -->
    - [x] Integrate Jurist audit phase into `tinytruce_sim.py` <!-- id: 80 -->
    - [x] Verify Jurist output in test run <!-- id: 81 -->

- [x] Critical Bug Fixes (Encountered during verify)
    - [x] Fix IndentationError in `tinytruce_sim.py`
    - [x] Fix UnicodeEncodeError (Windows UTF-8 wrap)
    - [x] Fix TinyWorld `.episodes` AttributeError
    - [x] Implement fallback parser for non-JSON Jurist output

- [ ] Post-Integration Polish
    - [ ] Remove diagnostic checkpoint prints from `tinytruce_sim.py` (Completed)
    - [x] Verify multi-agent history aggregation <!-- id: 82 -->
- [x] Performance & Scaling: Vatican Cyber-Schism (10 turns) <!-- id: 83 -->
    - [x] Run 10-turn simulation with Pope Leo & Elon Musk <!-- id: 84 -->
    - [x] Analyze final briefing and Jurist autopsy <!-- id: 85 -->
    - [x] Gap Analysis: Psychological vs. Structural Logic <!-- id: 108 -->
    - [x] Expand `STRATEGIC_BRIEFING_SCHEMA` with `psychological_structural_gap` <!-- id: 109 -->
    - [x] Update `ResultsExtractor` for "Bartender V2" tonality <!-- id: 110 -->
    - [x] Implement rendering in `tinytruce_briefing.md` <!-- id: 111 -->
    - [x] Integrate grounding-based "Structural Reality" check <!-- id: 112 -->
    - [x] Verify stability_index "RED" force-mode <!-- id: 113 -->
- [x] Physics of Failure: Quantitative Resource Projections <!-- id: 114 -->
    - [x] Expand `STRATEGIC_BRIEFING_SCHEMA` with `cost_of_non_compliance` <!-- id: 115 -->
    - [x] Update `ResultsExtractor` for "Forensic Math" tactical pivot <!-- id: 116 -->
    - [x] Implement rendering for "Section 7: The Physics of Failure" <!-- id: 117 -->
    - [x] Verify "Failure Horizon" calculation from Layer 1 logs <!-- id: 118 -->

- [x] Forensic Jurist Refinement: Truce Broker Pivot <!-- id: 86 -->
    - [x] Pivot Jurist to Mandatory Arbitrator (Prescriptive Settlement)
- [x] Implement 'Single Action' constraint to prevent loop-terminations
- [x] Verify Presidential-level output (Session: [3f964de6](file:///c:/Antigravity%20projects/TinyTruce/DOCUMENTS/runs/3f964de6/tinytruce_briefing.md))
    - [x] Fix JSON parsing/fallback for paratactic output <!-- id: 88 -->
    - [x] Verify settlement-focused audit in test run <!-- id: 89 -->

- [x] Stress Test: Ukraine Summit (15 turns) <!-- id: 90 -->
    - [x] Run 15-turn simulation with Putin, Zelensky, Trump <!-- id: 91 -->
    - [x] Validate stability and arbitration fidelity <!-- id: 92 -->

- [x] Stress Test v2: Enhanced Forensic Settlement (15 turns) <!-- id: 93 -->
    - [x] Run 15-turn simulation with enhanced rationale prompts <!-- id: 94 -->
    - [x] Verify depth and descriptive quality of the structural autopsy <!-- id: 95 -->
    - [x] Clarify Scorecard scale (/100) and stability index <!-- id: 96 -->
    - [x] Brainstorm presidential-level improvements in `jurist_brainstorming.md` <!-- id: 97 -->

- [x] Chronicler Fidelity Upgrade: 'Impact' Level Reporting
    - [x] Refactor `chronicler_update.py` with theater-specific probes <!-- id: 98 -->
    - [x] Implement Mandatory Fidelity Protocol (Specifics > Summaries) <!-- id: 99 -->
    - [x] Run high-density news harvest and verify output (SBU Drone Blitz detected) <!-- id: 100 -->

- [x] Chronicler Evolution: Global War Wire Pivot
    - [x] Update Implementation Plan for Global Tactical Desk <!-- id: 101 -->
    - [x] Refactor `chronicler_update.py` for Severity-First War Wire <!-- id: 102 -->
    - [x] Run Global Tactical Harvest <!-- id: 103 -->

- [x] Forensic Jurist Upgrade: Case Law Layer (Historical Precedents)
    - [x] Analyze East Timor/Algiers/Svalbard context <!-- id: 104 -->
    - [x] Inject Case Law operational physics into `tinytruce_sim.py` <!-- id: 105 -->
    - [x] Expand extraction schema to capture `precedent_matching` <!-- id: 106 -->
- [x] Jurist Multi-Pass Re-engineering: Sovereign Finality <!-- id: 119 -->
    - [x] Update `the_forensic_jurist.agent.json` (Identity Shift: Sovereign Auditor) <!-- id: 120 -->
    - [x] Implement "Math Injection" (Pass 1 Extractions -> Pass 2 Audit) <!-- id: 121 -->
    - [x] Enforce "Physics" Constraint & Linguistic Locks in audit prompt <!-- id: 122 -->
    - [x] Update `STRATEGIC_BRIEFING_SCHEMA` logic for "receipt-first" arbitration <!-- id: 123 -->
    - [x] Verify "Sovereign Finality" output in 10-turn simulation <!-- id: 124 -->

- [ ] Sovereign Autopsy Refinement: Sovereign Finality <!-- id: 125 -->
    - [x] Update `the_forensic_jurist.agent.json` (Anti-Wonk & Grime Anchors) <!-- id: 126 -->
    - [x] Refine `extraction_prompt` in `tinytruce_sim.py` (Sovereign Hook & Logic) <!-- id: 127 -->
    - [x] Update Section 9 Rendering (Sovereign Finality Template) <!-- id: 128 -->
    - [x] Verify "Sovereign Finality" output in 5-turn simulation <!-- id: 129 -->

- [x] Hardened Settlement Logic (Sovereign Settlement) <!-- id: 130 -->
    - [x] Update `the_forensic_jurist.agent.json` with 3 new core behaviors <!-- id: 131 -->
    - [x] Update `STRATEGIC_BRIEFING_SCHEMA` and Jurist extraction logic in `tinytruce_sim.py` <!-- id: 132 -->
    - [x] Run verification simulation to ensure direct assignment and lack of prescriptive terms <!-- id: 133 -->

- [x] Tonal Integrity & Midnight Hammer Enforcement <!-- id: 134 -->
    - [x] Update `psychological_structural_gap` with Sovereign Hook Format <!-- id: 135 -->
    - [x] Update `extraction_prompt` with Tonal Integrity Check and Midnight Hammer <!-- id: 136 -->
- [x] Finalize Test Suite Audit for Vertex AI <!-- id: 174 -->
    - [x] Audit unit tests in `tests/unit/` (Identified `test_atlas_auditor.py` and `test_universal_fidelity.py` issues) <!-- id: 175 -->
    - [x] Fix `test_atlas_auditor.py` I/O and grounding logic (Individual run passed) <!-- id: 176 -->
    - [x] Fix fragment fidelity (`syntax_constraints` string conversion) <!-- id: 180 -->
    - [x] Audit integration scenarios in `tests/scenarios/` (Fixed 3 Iran scenarios) <!-- id: 177 -->
    - [x] Verify all tests pass with Vertex AI endpoint <!-- id: 178 -->
- [x] Update documentation for Vertex AI test execution <!-- id: 179 -->
    - [x] Run 10-turn verification simulation of `amazon_debt_swap` <!-- id: 137 -->

- [x] Stability Drift (The Truce Half-Life) <!-- id: 138 -->
    - [x] Update `STRATEGIC_BRIEFING_SCHEMA` with `stability_half_life` <!-- id: 139 -->
    - [x] Update Section 3 Rendering to include Half-Life in `tinytruce_sim.py` <!-- id: 140 -->
    - [x] Update Jurist `extraction_prompt` with Half-Life Roast & Mandatory Re-Audit <!-- id: 141 -->
    - [x] Automated Output Fidelity Tester <!-- id: 143 -->
    - [x] Create `tests/unit/test_output_fidelity.py` with LLM-Auditor logic <!-- id: 144 -->
    - [x] Run fidelity tests for `the_forensic_jurist` and `bartender` <!-- id: 145 -->
    - [x] Verify test failure on intentionally bad inputs (sanity check) <!-- id: 146 -->
- [x] US-Iran Research Prompts for Deep Research <!-- id: 147 -->
    - [x] Draft prompt for Ali Larijani (Pragmatist/IRGC) <!-- id: 148 -->
    - [x] Draft prompt for Masoud Pezeshkian (Presidential constraints) <!-- id: 149 -->
    - [x] Draft prompt for Reza Pahlavi (Sovereign/Monarchist) <!-- id: 150 -->
- [x] Extract DNA & Build `ali_larijani.agent.json` + Fragments <!-- id: 152 -->
- [x] Extract DNA & Build `masoud_pezeshkian.agent.json` + Fragments <!-- id: 153 -->
- [x] Extract DNA & Build `reza_pahlavi.agent.json` + Fragments <!-- id: 154 -->
- [x] Integrate Reza Pahlavi into `test_output_fidelity.py` <!-- id: 155 -->
- [x] US-Iran Simulation Run: `middle_east_reset` (10 turns, Roast Nuke) <!-- id: 156 -->
- [x] US-Israel-Iran War Scenarios: The Trilogy of Collapse <!-- id: 157 -->
    - [x] Build `pezeshkians_gamble.json` (The Reformist Coup) <!-- id: 158 -->
    - [x] Build `larijani_pivot.json` (The Pragmatist Surrender) <!-- id: 159 -->
    - [x] Build `pahlavi_restoration.json` (The MIGA Protocol) <!-- id: 160 -->
- [x] Verification Simulation: `pezeshkians_gamble` <!-- id: 161 -->
- [x] Verification Simulation: `larijani_pivot` <!-- id: 162 -->
- [x] Verification Simulation: `miga_protocol_pahlavi` <!-- id: 163 -->
- [x] Implement Section 10: Structural Stability Levers <!-- id: 165 -->
    - [x] Update `STRATEGIC_BRIEFING_SCHEMA` in `tinytruce_sim.py` <!-- id: 166 -->
    - [x] Update `the_forensic_jurist.agent.json` with Sovereign Math lock <!-- id: 167 -->
    - [x] Verify output via 5-turn simulation <!-- id: 168 -->
- [x] Create Handover Brief (March 7th) <!-- id: 164 -->
- [x] Reroute Gemini API to Vertex AI <!-- id: 169 -->
    - [x] Update OpenAI Adapter Initialization in `tinytruce_sim.py` <!-- id: 170 -->
    - [x] Update `GeopoliticalCacheManager` in `tinytruce_sim.py` <!-- id: 171 -->
    - [x] Update `.env` with Vertex AI configuration <!-- id: 172 -->
- [x] Update `verify_cache.py` for Vertex AI compatibility.
- [x] Update `tests/testing_utils.py` (GeopoliticalCacheManager) for Vertex/Modern SDK.
- [x] Verify Vertex AI test completion.
- [x] Research and identify cheapest Vertex AI model ID (`gemini-2.5-flash-lite`) <!-- id: 173 -->
- [x] Debug and fix `llm_engine.py` for Vertex AI resource path compatibility
- [x] Fix missing Forensic Grounding for new agents in `Forensic_Intelligence_Atlas.md`
- [x] Successfully run 2-turn simulation on Vertex AI
- [x] Fix TypeError in `truncate_actions_or_stimuli` (NoneType check)
- [x] Standardize Vertex AI Context Cache ID (strip full resource path)
- [x] Fix TypeError in `_display_communication` (Safe target extraction)
- [x] Fix TypeError in `TinyWorld._push_and_display_latest_communication` (Safe content extraction)
- [x] Update War News API Scripts & Faculty <!-- id: 181 -->
    - [x] Update `mcp_war_news.py` endpoints and `.env` loading <!-- id: 182 -->
    - [x] Update `chronicler_update.py` `.env` loading <!-- id: 183 -->
    - [x] Geopolitical Chronicler: Cost & Engine Stabilization <!-- id: 185 -->
    - [x] Fix Zero-Cost Reporting in `llm_engine.py` (Unified usage capture) <!-- id: 186 -->
    - [x] Revert unstable `.parse()` and debug prints from OpenAI adapter <!-- id: 187 -->
    - [x] Implement `TINYTRUCE_FORCE_NATIVE_LLM` in `openai_utils.py` <!-- id: 188 -->
    - [x] Update `chronicler_update.py` to force Native Gemini path <!-- id: 189 -->
    - [x] Verify cost reporting and report generation in final chronicler run <!-- id: 190 -->
- [x] Hardening Native Gemini Engine & API Integrity <!-- id: 191 -->
    - [x] Audit unit tests (`tests/unit/`) for Vertex AI compatibility <!-- id: 192 -->
    - [x] Identify "System fallback" root cause (Prompt/Schema Clash & Engine Regressions) <!-- id: 193 -->
    - [x] Implement robust JSON "best-effort" repair in `llm_engine.py` (Both Engines) <!-- id: 194 -->
    - [x] Fix Pydantic `Action` schema missing `target` field causing multi-block JSON dumps <!-- id: 198 -->
    - [x] Document detailed Handover Brief for next session <!-- id: 197 -->
    - [x] Verify Jurist and other agents in `test_jurist_audit.py` pass without fallbacks or raw texts <!-- id: 196 -->
    - [x] Update `README.md` and `FRONTEND_NOTES.md` with JSON repair and schema resilience notes <!-- id: 199 -->

TinyTruce: Roadmap to Production (Backend & Infrastructure)
Now that the core simulation engine is stable (v2.4), we need to transition from a research-oriented CLI tool to a scalable, containerized backend.

1. Backend Hardening (The "Cleaning" Phase)
Before we wrap this in an MCP server, we need to remove the "scaffolding":

 Remove/Archive Legacy Scripts: Move utility scripts like 
test_cost.py
, 
test_vertex_ai.py
, and 
discover_models.py
 into a utils/legacy directory.
 Dotenv Enforcements: Ensure 
tinytruce_sim.py
 and tinytroupe/ only look for configuration through environment variables, removing hardcoded file paths where possible.
 State Centralization: Transition from purely file-based storage (DOCUMENTS/runs) to a structured approach (e.g., using a /data volume for the Docker container).
2. FastMCP Integration
Standardizing the simulation as a proper Model Context Protocol (MCP) server:

 Create server.py: Implement a FastMCP wrapper that exposes the simulation as a set of tools:
run_geopolitical_sim(scenario, turns, agents)
get_active_reports()
analyze_grounding(agent_name)
 Async Job Management: Simulations take minutes. We need a way for the MCP server to start a task and return a job_id, rather than blocking.
3. Dockerization & Deployment
 Create Dockerfile: A multi-stage build to keep the image slim.
 Environment Sealing: Use docker-compose to handle secrets for Google Cloud (Vertex AI) and other APIs without committing them to the repo.
 FTP / Deployment: Scripted synchronization for deploying the containerized backend to your server.
4. Frontend Hooks
 SSE / WebSockets: Expose real-time telemetry (the "Psy-momentum" and "Calculating..." status) via an endpoint for the future frontend.
 JSON Report Standard: Formalize the output of tinytruce_results.json so the frontend can render it as a rich dashboard.
IMPORTANT

The primary goal here is to make the backend headless. It should no longer rely on sys.stdout for critical status, but rather emit structured events that an MCP client or Frontend can consume.
