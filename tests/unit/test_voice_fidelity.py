import sys
import os
import pytest
import json
from unittest.mock import MagicMock, patch

# FORCE LOCAL IMPORT
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import tinytroupe
from tinytroupe.agent import TinyPerson

print(f"DEBUG: tinytroupe file: {tinytroupe.__file__}")
print(f"DEBUG: test file: {__file__}")

def test_voice_fidelity_elon_musk_hardcore():
    """
    Verifies that the TinyPerson engine correctly parses and injects 
    'vocabulary_priority' and 'syntax_constraints' into the system prompt.
    """
    # 1. Setup the Agent paths
    # We need absolute paths for load_specification and import_fragment
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    agent_path = os.path.join(project_root, "personas", "agents", "elon_musk.agent.json")
    frag_path = os.path.join(project_root, "personas", "fragments", "elon_musk_reformer.fragment.json")
    
    # 2. Instantiate and Harden
    # We use load_specification with a unique name to avoid conflicts
    agent = TinyPerson.load_specification(agent_path, new_agent_name="Elon_Hardcore_Test")
    agent.import_fragment(frag_path)
    
    print(f"DEBUG: Agent Persona Keys: {agent._persona.keys()}")
    print(f"DEBUG: vocabulary_priority: {agent._persona.get('vocabulary_priority')}")
    print(f"DEBUG: syntax_constraints: {agent._persona.get('syntax_constraints')}")
    
    # 3. Verify the Prompt Injection (The "Linguistic Lock")
    system_content = agent.current_messages[0]['content']
    
    assert "### FRAGMENT LINGUISTIC LOCKS (STRICT ENFORCEMENT)" in system_content
    assert "VOCABULARY PRIORITY:" in system_content
    assert "Hardcore" in system_content
    assert "Impedance Mismatch" in system_content
    assert "First Principles" in system_content
    assert "SYNTAX & RHETORICAL RULES:" in system_content
    assert "Avoid adjectives like 'great'" in system_content
    
    # 4. Mock the LLM to verify the TALK action flow still works with the new prompt
    with patch("tinytroupe.openai_utils.client") as mock_client_func:
        mock_client = MagicMock()
        mock_client_func.return_value = mock_client
        
        # Mocking a response that obeys the constraints
        mock_response = {
            "action": {
                "type": "TALK", 
                "content": "This is an impedance mismatch of the highest order. We needs a hardcore first-principles audit.", 
                "target": "everyone"
            },
            "cognitive_state": {
                "goals": "Fix the grid", 
                "attention": "Production bottlenecks", 
                "emotions": "Focused", 
                "emotional_intensity": 1.0
            }
        }
        
        mock_client.send_message.return_value = {
            "role": "assistant",
            "content": json.dumps(mock_response)
        }
        
        # 5. Trigger Action
        # We need to act once to verify the output flow.
        # We set until_done=False because we are specifying a fixed number of actions (n=1).
        actions = agent.act(until_done=False, n=1, return_actions=True)
        
        # 6. Verification of the action contents
        talk_action = actions[0]['action']
        assert talk_action['type'] == "TALK"
        assert "hardcore" in talk_action['content'].lower()
        assert "impedance mismatch" in talk_action['content'].lower()
        
        print(f"\n[SUCCESS] Voice Fidelity: Verified that the 'Linguistic Lock' section is present in the prompt and handled correctly by the agent.")

def test_fragment_stacking_linguistic_logic():
    """
    Verifies that multiple fragments correctly concatenate vocabulary
    and overwrite syntax constraints.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    agent_path = os.path.join(project_root, "personas", "agents", "elon_musk.agent.json")
    
    agent = TinyPerson.load_specification(agent_path, new_agent_name="Elon_Stack_Test")
    
    # Fragment 1: Reformer
    frag_1 = os.path.join(project_root, "personas", "fragments", "elon_musk_reformer.fragment.json")
    agent.import_fragment(frag_1)
    
    # Fragment 2: Savior
    frag_2 = os.path.join(project_root, "personas", "fragments", "savior.fragment.json")
    agent.import_fragment(frag_2)
    
    # Verification
    system_content = agent.current_messages[0]['content']
    
    # Vocabulary should be CONCATENATED
    assert "Hardcore" in system_content
    assert "Moral Baseline" in system_content
    assert "Covenant" in system_content
    
    # Syntax should be OVERWRITTEN (Savior was last)
    assert "Rule of Threes" in system_content
    # The Elon constraint should NOT be present if it was overwritten
    # Wait, merge_dicts(overwrite=True) will overwrite scalars. 
    # Let's verify if "Avoid adjectives" is gone.
    assert "Avoid adjectives like 'great'" not in system_content
    
    print(f"\n[SUCCESS] Fragment Stacking: Verified concatenated vocabulary and overwritten syntax constraints.")

if __name__ == "__main__":
    pytest.main([__file__])
