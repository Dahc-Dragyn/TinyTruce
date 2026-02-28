import pytest
from unittest.mock import MagicMock, patch
from tinytroupe.agent import TinyPerson

def test_loop_guardsman_interruption():
    """
    Verifies that a TinyPerson is forcibly stopped if it exceeds MAX_ACTIONS_BEFORE_DONE.
    """
    # 1. Setup the environment
    # We set the limit to 2, meaning it should stop after the 3rd action attempt
    TinyPerson.MAX_ACTIONS_BEFORE_DONE = 2
    
    # Create a dummy agent
    agent = TinyPerson("LoopingAgent")
    
    # 2. Mock the message production to NEVER return a 'DONE' action
    # We want it to just keep suggesting 'TALK'
    mock_action = {'type': 'TALK', 'content': 'I will never stop talking!', 'target': 'everyone'}
    
    with patch.object(agent, '_produce_message') as mock_produce:
        # Mocking the return of _produce_message. 
        # In TinyTroupe, _produce_message returns (role, content_dict)
        mock_produce.return_value = ("assistant", {
            "action": mock_action, 
            "cognitive_state": {
                "goals": "Stay in this loop",
                "attention": "The conversation",
                "emotions": "Stubborn"
            }
        })
        
        # 3. Trigger the action loop
        # until_done=True will keep calling aux_act_once until 'DONE' or the guard triggers
        actions = agent.act(until_done=True, return_actions=True)
        
        # 4. Verify the guard triggered
        # If MAX_ACTIONS_BEFORE_DONE is 2:
        # Turn 1: 1 action (len 1)
        # Turn 2: 2 actions (len 2)
        # Turn 3: 3 actions (len 3) -> len > 2 is TRUE -> BREAK
        assert len(actions) == 3
        
        # Verify it never issued a DONE
        for a in actions:
            assert a['action']['type'] == 'TALK'
            
        print(f"\n[SUCCESS] Guard triggered after {len(actions)} actions. Infinite loop prevented.")

def test_loop_guardsman_no_interruption_on_done():
    """
    Verifies that the guard does NOT trigger if the agent actually says DONE.
    """
    TinyPerson.MAX_ACTIONS_BEFORE_DONE = 2
    agent = TinyPerson("GoodAgent")
    
    # Mock produce message to return TALK then DONE
    with patch.object(agent, '_produce_message') as mock_produce:
        mock_produce.side_effect = [
            ("assistant", {
                "action": {'type': 'TALK', 'content': 'First', 'target': 'everyone'}, 
                "cognitive_state": {
                    "goals": "Be helpful",
                    "attention": "The user",
                    "emotions": "Happy"
                }
            }),
            ("assistant", {
                "action": {'type': 'DONE', 'content': 'Finished', 'target': 'everyone'}, 
                "cognitive_state": {
                    "goals": "Be helpful",
                    "attention": "The user",
                    "emotions": "Satisfied"
                }
            })
        ]
        
        actions = agent.act(until_done=True, return_actions=True)
        
        # Should have exactly 2 actions
        assert len(actions) == 2
        assert actions[-1]['action']['type'] == 'DONE'
        print(f"[SUCCESS] Agent finished naturally with {len(actions)} actions.")
