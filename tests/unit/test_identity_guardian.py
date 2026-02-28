import pytest
import json
from unittest.mock import MagicMock, patch
from tinytroupe.agent import TinyPerson
from tinytruce_sim import compress_agent_memory

def test_identity_guardian_preserves_system_message():
    """
    Verifies that compress_agent_memory prunes the episodic memory but 
    preserves the core system message (Identity).
    """
    # 1. Setup the Agent
    agent = TinyPerson("IdentityAgent")
    # Set a unique identity/system message factor
    agent.define("bio", "I am a high-stakes geopolitical strategist with a focus on de-escalation.")
    agent.reset_prompt()
    
    initial_system_content = agent.current_messages[0]['content']
    assert "geopolitical strategist" in initial_system_content
    
    # 2. Fill memory with fake episodes
    # We'll use a window_size of 8 and prune_count of 4 like in tinytruce_sim.py
    for i in range(10):
        agent.store_in_memory({
            "role": "user", 
            "content": f"Turn {i}", 
            "type": "stimuli", 
            "simulation_timestamp": "2026-01-01T00:00:00"
        })
    
    # Verify memory is full
    assert agent.episodic_memory.count() == 10
    
    # 3. Mock the LLM summarizer
    # compress_agent_memory calls openai_utils.client().send_message
    with patch("tinytroupe.openai_utils.client") as mock_client_func:
        mock_client = MagicMock()
        mock_client_func.return_value = mock_client
        mock_client.send_message.return_value = {"content": "Summary: Things happened."}
        
        # 4. Trigger Compression
        # Usage: compress_agent_memory(participants, window_size=12, prune_count=6)
        compress_agent_memory([agent], window_size=8, prune_count=4)
        
        # 5. Verification
        # Memory should be reduced from 10 to 6 (10 - 4)
        assert agent.episodic_memory.count() == 6
        
        # Identity Check: The first message in current_messages must STILL be the system message
        # reset_prompt() is called inside compress_agent_memory, which rebuilds current_messages
        assert agent.current_messages[0]['role'] == "system"
        assert "geopolitical strategist" in agent.current_messages[0]['content']
        
        # Anchor Check: Verify the summary was archived to anchors
        assert hasattr(agent, '_episodic_anchors')
        assert len(agent._episodic_anchors) == 1
        assert agent._episodic_anchors[0] == "Summary: Things happened."
        
        print(f"\n[SUCCESS] Identity Guardian: Verified that system message was preserved and memory was pruned.")

if __name__ == "__main__":
    pytest.main([__file__])
