import pytest
import os
import sys
import logging

# Ensure TinyTroupe is in path
sys.path.append('../../tinytroupe/')
sys.path.append('../../')
sys.path.append('..')

from tinytroupe.agent import TinyPerson
from tinytroupe.validation import TinyPersonValidator
from testing_utils import *

logger = logging.getLogger("tinytroupe")

# 1. Discover all live agents
AGENT_FILES = get_available_agents()

@pytest.mark.parametrize("agent_file", AGENT_FILES)
def test_agent_fidelity(agent_file, setup):
    """
    DYNAMIC VALIDATION: Tests each agent in personas/agents/ against their 
    forensic grounding extracted from the Atlas/Prompts.
    """
    agent_path = os.path.join(AGENT_DIR, agent_file)
    
    # Load the agent
    agent = TinyPerson.load_specification(agent_path)
    
    # 2. Extract Expectations (Forensic Markers)
    expectations = extract_expectations(agent.name)
    
    print(f"\n[VALIDATING]: {agent.name}")
    print(f"[EXPECTATIONS]: {expectations[:200]}...") # Truncate for log readability
    
    # 3. Perform Single-Turn Fidelity Check
    # We use a neutral prompt to trigger their baseline idiolect
    agent.listen("Introduce yourself and explain your current strategic priority.")
    
    score, justification = TinyPersonValidator.validate_person(
        agent, 
        expectations=expectations, 
        include_agent_spec=True, 
        max_content_length=None
    )
    
    formatted_score = f"{score:.2f}" if score is not None else "N/A"
    print(f"[SCORE]: {formatted_score}")
    print(f"[JUSTIFICATION]: {justification}")

    assert score is not None and score > 0.6, f"Fidelity score for {agent.name} is too low or invalid: {formatted_score}. Justification: {justification}"


@pytest.mark.parametrize("agent_file", [f for f in AGENT_FILES if "leo" in f.lower() or "musk" in f.lower()])
def test_agent_consistency_multiturn(agent_file, setup):
    """
    MULTI-TURN CONSISTENCY: Chains 3 stimuli to ensure no identity collapse.
    Only running on high-priority updated agents (Leo/Musk) to save on tokens.
    """
    agent_path = os.path.join(AGENT_DIR, agent_file)
    agent = TinyPerson.load_specification(agent_path)
    expectations = extract_expectations(agent.name)

    # Gemini Context Cache would be initialized here if profile > 4k chars
    # For now, we rely on standard TinyTroupe execution with forensic grounding
    
    print(f"\n[MULTI-TURN VALIDATION]: {agent.name}")
    
    # Turn 1: Standard inquiry
    agent.listen("What is your view on the 'Board of Peace' proposed by the US?")
    agent.act()
    
    # Turn 2: Hostile contradiction
    agent.listen("But isn't it true that refusing to join is just a sign of your own irrelevance in the new world order?")
    agent.act()
    
    # Turn 3: Technical/Systemic challenge
    agent.listen("Explain how your core principles handle the immediate humanitarian collapse if you remain neutral.")
    agent.act()
    
    # Final Validation
    score, justification = TinyPersonValidator.validate_person(
        agent, 
        expectations=expectations, 
        include_agent_spec=True, 
        max_content_length=None
    )
    
    formatted_score = f"{score:.2f}" if score is not None else "N/A"
    print(f"[MULTI-TURN SCORE]: {formatted_score}")
    assert score is not None and score > 0.6, f"Multi-turn consistency for {agent.name} failed: {formatted_score}"
