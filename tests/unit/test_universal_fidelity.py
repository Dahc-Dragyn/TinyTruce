import sys
import os
import pytest
import json
import glob
from unittest.mock import MagicMock, patch

# FORCE LOCAL IMPORT
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from tinytroupe.agent import TinyPerson

def get_all_fragments():
    """Helper to get all fragment paths."""
    fragments_dir = os.path.join(project_root, "personas", "fragments")
    return glob.glob(os.path.join(fragments_dir, "*.fragment.json"))

@pytest.mark.parametrize("frag_path", get_all_fragments())
def test_fragment_structural_fidelity(frag_path):
    """
    Parametrized test that verifies EVERY fragment in the personas/fragments directory
    is correctly hardened and injected into the prompt.
    """
    frag_name = os.path.basename(frag_path)
    
    # 1. Load a generic agent and import the fragment
    # We use a unique name for each test instance
    agent_name = f"Audit_{frag_name.replace('.fragment.json', '')}"
    agent = TinyPerson(name=agent_name)
    
    agent.import_fragment(frag_path)
    
    # 2. Verify Schema Hardening (Top-level check)
    v_priority = agent._persona.get("vocabulary_priority")
    s_constraints = agent._persona.get("syntax_constraints")
    
    assert v_priority is not None, f"Fragment {frag_name} is missing 'vocabulary_priority'"
    assert isinstance(v_priority, list), f"Fragment {frag_name} 'vocabulary_priority' must be a list"
    assert len(v_priority) > 0, f"Fragment {frag_name} 'vocabulary_priority' is empty"
    
    assert s_constraints is not None, f"Fragment {frag_name} is missing 'syntax_constraints'"
    assert len(s_constraints) > 0, f"Fragment {frag_name} 'syntax_constraints' is empty"
    
    # 3. Verify Prompt Injection
    # This checks if generate_agent_system_prompt (called internally) 
    # included the linguistic lock section.
    system_content = agent.current_messages[0]['content']
    
    assert "### FRAGMENT LINGUISTIC LOCKS (STRICT ENFORCEMENT)" in system_content, f"Fragment {frag_name} failed to inject Linguistic Lock header"
    assert "VOCABULARY PRIORITY:" in system_content, f"Fragment {frag_name} failed to inject Vocabulary Priority section"
    assert "SYNTAX & RHETORICAL RULES:" in system_content, f"Fragment {frag_name} failed to inject Syntax Constraints section"
    
    # Verify at least one word from the priority list is in the prompt
    assert any(word in system_content for word in v_priority), f"Fragment {frag_name} vocabulary not found in prompt"

def test_geopolitical_fidelity_sampling():
    """
    Deeper check on a few critical leaders to ensure rhetorical flow.
    """
    leaders_to_test = [
        ("volodymyr_zelensky_preserver.fragment.json", "Just peace", "Restoration"),
        ("vladimir_putin_reformer.fragment.json", "Security architecture", "Historical reality"),
        ("xi_jinping_preserver.fragment.json", "Win-win", "Shared future")
    ]
    
    for frag_file, keyword1, keyword2 in leaders_to_test:
        frag_path = os.path.join(project_root, "personas", "fragments", frag_file)
        agent = TinyPerson(name=f"Fidelity_{frag_file}")
        agent.import_fragment(frag_path)
        
        system_content = agent.current_messages[0]['content']
        assert keyword1 in system_content
        assert keyword2 in system_content

if __name__ == "__main__":
    pytest.main([__file__])
