import pytest
import os
import json
import glob

# Project Path Setup
_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCENARIO_DIR = os.path.join(_ROOT_DIR, "scenarios")
AGENT_DIR = os.path.join(_ROOT_DIR, "personas", "agents")
FRAGMENT_DIR = os.path.join(_ROOT_DIR, "personas", "fragments")

def get_all_scenarios():
    """Returns a list of all scenario JSON files."""
    return glob.glob(os.path.join(SCENARIO_DIR, "*.json"))

@pytest.mark.parametrize("scenario_path", get_all_scenarios())
def test_scenario_forensic_integrity(scenario_path):
    """
    Audits a scenario file for broken links to agents, fragments, and grounding data.
    """
    scenario_name = os.path.basename(scenario_path)
    
    with open(scenario_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Scenario {scenario_name} is not valid JSON: {e}")

    # 1. Check Grounding Assets
    # Scenarios use 'grounding_payload' or 'grounding_files'
    grounding = data.get("grounding_payload", [])
    if not grounding:
        grounding = data.get("grounding_files", [])
        
    for g_path in grounding:
        full_g_path = os.path.join(_ROOT_DIR, g_path)
        assert os.path.exists(full_g_path), f"[{scenario_name}] Missing Grounding File: {g_path}"

    # 2. Check Agents (if specified)
    # Some scenarios have 'agents' list, others might just be broad descriptions
    agents = data.get("agents", [])
    for agent in agents:
        # Check if it's a filename or just a name
        if not agent.endswith(".json"):
            agent_file = f"{agent}.agent.json"
        else:
            agent_file = agent
            
        full_agent_path = os.path.join(AGENT_DIR, agent_file)
        assert os.path.exists(full_agent_path), f"[{scenario_name}] Missing Agent Profile: {agent_file}"

    # 3. Check Fragments
    # Fragments are usually behavior overlays
    fragments = data.get("fragments", [])
    for frag in fragments:
        if not frag.endswith(".json"):
            frag_file = f"{frag}.fragment.json"
        else:
            frag_file = frag
            
        full_frag_path = os.path.join(FRAGMENT_DIR, frag_file)
        assert os.path.exists(full_frag_path), f"[{scenario_name}] Missing Fragment: {frag_file}"

def test_global_asset_registry():
    """
    Verifies that all core engine files are present.
    """
    essential_files = [
        os.path.join(_ROOT_DIR, "personas", "agents", "Forensic_Intelligence_Atlas.md"),
        os.path.join(_ROOT_DIR, "tinytruce_sim.py"),
        os.path.join(_ROOT_DIR, "DOCUMENTS", "README.md")
    ]
    for ef in essential_files:
        assert os.path.exists(ef), f"Critical engine asset missing: {os.path.basename(ef)}"

if __name__ == "__main__":
    pytest.main([__file__])
