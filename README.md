# TinyTruce: Geopolitical Conflict Lab (2026) 🌍🤝

> *“Peace is not the absence of conflict, but the presence of creative alternatives for responding to conflict.”* — Dorothy Thompson

**TinyTruce** is a specialized fork of Microsoft's [TinyTroupe](https://github.com/microsoft/tinytroupe), re-engineered for high-fidelity geopolitical simulations. It places AI agents—representing world leaders, tech CEOs, and religious figures—into complex, near-future scenarios (2025-2026) to explore negotiation dynamics, red lines, and potential de-escalation pathways.

Unlike standard agent simulations that focus on generic interactions, TinyTruce is built on **Forensic Grounding**: every scenario is backed by real-world treaties, technical whitepapers, and economic reports to ensure the agents are debating facts, not hallucinations.

---

## 🚀 Key Features

### 1. Forensic Grounding (Layer 0)
Agents are not just prompted with a name; they are injected with deep, factual context.
- **Data Ingestion**: Specific files (e.g., `data/treaties/1959-nile-water-agreement.txt`, `data/tech/euroguard-v-audit-leak.txt`) are loaded into the agent's memory *before* the simulation starts.
- **World State**: A global context file (`data/facts/world-facts.2026.txt`) ensures all agents share the same timeline and geopolitical reality.

### 2. The Scenario Board (Layer 1)
Scenarios are defined in JSON files in the `scenarios/` directory. Each scenario includes:
- **Initial Broadcast**: The "breaking news" that starts the conflict.
- **Intervention Protocol**: A predefined "Peace Bomb" or "Crisis Escalation" that triggers if the agents reach a stalemate.
- **Scenario Allegory Map (SAM)**: A "Shadow Dictionary" of allegories (e.g., "Heresy" -> "Signal Drift") that allows agents to discuss sensitive topics without triggering safety filters.

### 3. Advanced Resilience (Layer 2)
To maintain simulation integrity during high-stakes theological or political debates, TinyTruce implements:
- **Diplomatic Pivots**: If an LLM response is blocked by safety filters, the agent automatically pivots to a persona-specific "safe" response (e.g., "The Church does not negotiate with echoes") instead of crashing.
- **Forensic Allegories**: Agents are prompted to use metaphorical language to bypass keyword-based filters while retaining semantic intensity.

### 4. The Narrator & Roast Mode (Layer 2.5)
- **Narrator**: A "Salty British Documentarian" who provides dry, observational commentary every 5 turns.
- **Roast Recap**: At the end of the simulation, a "Jaded UN Bartender" generates a gossip-heavy summary of the participants' egos and maneuvers.

---

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd TinyTruce
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: TinyTruce relies on `tinytroupe`, `rich`, `openai`, and `google-generativeai`)*

4.  **Configure API Keys**:
    - Create a `.env` file or set environment variables for `OPENAI_API_KEY` (or `GOOGLE_API_KEY` if using Gemini).
    - Checks `config.ini` for model settings.

---

## 📖 Usage

### Running a Simulation

Use the `tinytruce_sim.py` script to launch a scenario.

**Basic Usage:**
```bash
python tinytruce_sim.py --scenario <scenario_key>
```

**Advanced Usage (Vatican Cyber-Schism):**
```bash
python tinytruce_sim.py --scenario vatican_cyber-schism --turns 15 --agents pope_leo.agent.json yann_lecun.agent.json sam_altman.agent.json --fragments pope_leo_preserver.fragment.json purist_reformer.fragment.json reformer.fragment.json --narrator salty --roast-level nuclear
```

### Available Scenarios (`scenarios/`)
-   `vatican_cyber-schism`: Pope Leo XIV vs. Tech CEOs on AI "Souls" and Digital Sacraments.
-   `neural_sovereignty_accord`: EU regulators vs. US Tech Giants on "Cognitive Data Rights".
-   `lunar_gateway_jurisdiction`: US vs. China vs. Private Sector on lunar mining rights.
-   `lithium_triangle_leverage`: South American leaders vs. Global Markets on lithium nationalization.
-   `blue_nile_brinkmanship`: Egypt vs. Ethiopia on the Grand Ethiopian Renaissance Dam (GERD).

### Viewing Results
After a simulation completes, check the following files:
-   `tinytruce_briefing.md`: A formal strategic audit of the negotiation, including a "Resolve Scorecard" and "Redline Breach Report".
-   `tinytruce_roast.md`: The "Jaded UN Bartender" recap.
-   `tinytruce_results.json`: Raw data export.
-   `tinytruce_simulation.log`: Full debug logs (if enabled in `config.ini`).

---

## 📂 Project Structure

```
TinyTruce/
├── data/                   # Forensic Grounding Files
│   ├── facts/              # Global world state (2026)
│   ├── treaties/           # Real-world treaty texts
│   ├── tech/               # Technical whitepapers/leaks
│   ├── economics/          # IMF/World Bank reports
│   └── theology/           # Religious encyclicals
├── personas/               # Agent Definitions
│   ├── agents/             # Base profiles (Pope, LeCun, Altman, etc.)
│   └── fragments/          # Behavioral overlays (Preserver, Reformer)
├── scenarios/              # Scenario JSON configurations
├── tinytroupe/             # Core library (Modified)
│   ├── agent/              # TinyPerson logic (Resilience)
│   └── ...
├── tinytruce_sim.py        # Main simulation entry point
├── config.ini              # Configuration (Models, Logging)
└── requirements.txt        # Python dependencies
```

---

## ⚖️ Disclaimer

**TinyTruce** is an experimental research tool that uses Large Language Models (LLMs) to generate content. The output is stochastic and may contain hallucinations or inaccuracies. The views expressed by the simulated agents do not reflect the views of the creators or any affiliated organizations. This tool is for **imagination enhancement** and **strategic exploration** only.

*Based on [TinyTroupe](https://github.com/microsoft/tinytroupe) by Microsoft Research.*
