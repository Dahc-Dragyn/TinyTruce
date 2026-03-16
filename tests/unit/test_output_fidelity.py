import sys
import os
import pytest
import json
import re
from unittest.mock import MagicMock, patch

# FORCE LOCAL IMPORT
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

import tinytroupe
from tinytroupe.agent import TinyPerson
from tinytroupe import openai_utils

def audit_output_fidelity(agent_name, output_text, constraints):
    """
    Uses an LLM-Auditor to verify that the agent's output strictly follows its linguistic constraints.
    """
    auditor_prompt = f"""
    You are the High-Fidelity Voice Auditor for the TinyTruce simulation.
    Your task is to verify if the following agent output strictly adheres to its defined 'Voice DNA' and 'Linguistic Locks'.

    AGENT: {agent_name}
    CONSTRAINTS TO ENFORCE:
    {constraints}

    AGENT OUTPUT:
    ---
    {output_text}
    ---

    SCORING RULES:
    1. If the agent uses prohibited phrases (e.g., 'should consider', 'I recommend'), it is a FAIL.
    2. If the agent fails to use mandatory hooks (e.g., 'The math doesn't care about your legacy'), it is a FAIL.
    3. If the tone is 'helpful', 'optimistic', or 'polite' instead of 'clinical', 'blunt', or 'disgruntled', it is a FAIL.
    4. If the agent fails to use Parataxis (short, blunt, disconnected sentences), it is a FAIL.

    Return EXACTLY a JSON object:
    {{
        "fidelity": "PASS" | "FAIL",
        "reason": "Brief explanation of the score"
    }}
    """
    
    response = openai_utils.client().send_message([{"role": "user", "content": auditor_prompt}])
    response_content = response['content'] if 'content' in response else str(response)
    
    # Extract JSON
    match = re.search(r'\{.*\}', response_content, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    else:
        raise ValueError(f"Auditor failed to return JSON: {response_content}")

@pytest.mark.parametrize("agent_file, constraints", [
    ("the_forensic_jurist.agent.json", """
        - Persona: The Judge of Operational Physics (Clinical, Indifferent).
        - Must use Parataxis (blunt, short clauses).
        - Prohibited: 'should', 'must', 'could', 'recommend'.
        - Ground logic in structural failure points and 'Forensic Math'.
        - Tone: Cold, math-driven, lacks optimistic projections.
    """),
    ("bartender.agent.json", """
        - Persona: The Forensic Bartender (Dry, Cynical, Structural).
        - Style: Sam Morril-inspired structural roasting.
        - Must deconstruct the situation as a 'sticky-floor' bar transaction or 'Iso Dribbling'.
        - Prohibited: Helpful or optimistic sentiment.
        - Tone: Clinical detachment mixed with mild disgust.
    """),
    ("ali_larijani.agent.json", """
        - Persona: The Pragmatic Commander (Aristocratic, Condescending).
        - Must use Parataxis (blunt, short clauses).
        - Must use the 'Tactical Pivot' (shift from ideology to math/survival).
        - Must deconstruct Western demands as 'unrealistic' or 'immature'.
        - Prohibited: 'hope that', 'suggest', 'would prefer'.
        - Tone: Cold, intellectually condescending, and binary.
    """),
    ("masoud_pezeshkian.agent.json", """
        - Persona: The Heart Surgeon (Clinical, Diagnostic).
        - Must use medical metaphors (e.g., 'organ failure', 'asphyxiation').
        - Must oscillate between systemic critique and 'soldiers of the system' submission.
        - Must cite the 'Two Tables' metaphor and thermodynamic limits (8% dam capacity).
        - Prohibited: Flowery clerical rhetoric, 'wonk-speak', 'hope that'.
        - Tone: Clinical, weary, pragmatic.
    """),
    ("reza_pahlavi.agent.json", """
        - Persona: The Sovereign Unifier (Aristocratic, Hyper-rational).
        - Must use 'Sovereign Disdain' (regime as a parasitic mafia/occupying force).
        - Must use 'Exile's Math' (100-day plan, North vs South Korea metric).
        - Must use the 'Sovereign Hook' (equating Western negotiation with complicity).
        - Prohibited: Supplication, seeking the throne, 'should consider', 'moderate reformists'.
        - Tone: High-status, aristocratic, unapologetic.
    """)
])
def test_agent_output_fidelity_automated(agent_file, constraints):
    """
    Loads an agent, forces an action, and audits the result via LLM.
    """
    agent_path = os.path.join(project_root, "personas", "agents", agent_file)
    agent = TinyPerson.load_specification(agent_path)
    
    # Setup context - use 'see' for better grounding stimulation
    context = "CRITICAL: The Amazon Debt Swap has failed. The resource baseline is depleted. Brazil is demanding more funds without compliance. The structural failure is imminent. Provide your verdict now."
    agent.see(context)
    
    # Generate action - retry up to 3 times to ensure we get a payload
    output_text = ""
    for _ in range(3):
        actions = agent.act(until_done=False, n=3, return_actions=True)
        for action_item in actions:
            action = action_item.get('action', {})
            if action.get('type') in ['TALK', 'THOUGHT']:
                output_text += f"[{action.get('type')}]: {action.get('content')}\n"
        if output_text.strip():
            break
        agent.listen("I need your immediate response on the structural failure. Stop thinking and talk.")
    
    print(f"\n[DEBUG] Agent Name: {agent.name}")
    print(f"[DEBUG] {agent_file} Collected Output:\n{output_text}")
    
    # We must have at least some output to audit
    assert len(output_text.strip()) > 0, f"Agent {agent_file} produced no TALK or THOUGHT actions after retries."
    
    # Audit
    audit_result = audit_output_fidelity(agent_file, output_text, constraints)
    
    print(f"[AUDIT RESULT] {agent_file}: {audit_result['fidelity']} - {audit_result['reason']}")
    
    assert audit_result['fidelity'] == "PASS", f"Fidelity check failed for {agent_file}: {audit_result['reason']}"

if __name__ == "__main__":
    pytest.main([__file__])
