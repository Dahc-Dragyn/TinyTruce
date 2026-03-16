import os
import json
from tinytroupe.agent import TinyPerson
import tinytroupe.openai_utils as openai_utils
from dotenv import load_dotenv

load_dotenv()

# Set required environment variables for TinyTroupe
os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
if os.getenv("GOOGLE_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

def test_jurist():
    print("--- Initializing The Forensic Jurist ---")
    jurist = TinyPerson.load_specification("personas/agents/the_forensic_jurist.agent.json")
    
    physics_receipt = """### PHYSICS_OF_FAILURE_RECEIPT (MANDATORY GROUNDING) ###
- Participant: Russia
  - Depletion Event: Munitions
  - Threshold Alert: 12
  - Failure Horizon: 60 days
- Participant: Ukraine
  - Depletion Event: Manpower
  - Threshold Alert: 15
  - Failure Horizon: 90 days
"""

    audit_prompt = f"""
    {physics_receipt}
    
    ### MANDATORY ARBITRATION MANDATE (SOVEREIGN AUDITOR) ###
    You are The Forensic Jurist, the Judge of Operational Physics.
    The math doesn't care about your legacy. Here is your receipt.
    
    ### LINGUISTIC LOCKS ###
    1. Every verdict must start with: "The math doesn't care about your legacy. Here is your receipt."
    2. Use Sovereign Parataxis: Blunt, disconnected clauses. Avoid diplomatic filler. 
    3. Use logic: "The door is shut. Munitions are zero. Move the border."
    
    ### WORLD HISTORY FOR REVIEW ###
    Sample History: Putin and Zelenskyy are arguing about NATO and 1991 borders.
    
    ### CASE LAW PRECEDENTS (OPERATIONAL PHYSICS) ###
    You MUST anchor your settlement to one of the following historical frameworks:
    1. **1999 East Timor (UNTAET)**: For sovereignty escrow, deferred referendums, or transitional administrations.
    2. **1981 Algiers Accords**: For asset escrow, financial arbitration, and conditionality-based fund releases.
    3. **1920 Svalbard Treaty**: For demilitarized, neutral zones where sovereignty is recognized but military use is forbidden and equal economic access is guaranteed.
    
    ### THE TASK ###
    You are forbidden from offering a 'peace vibe'. 
    You must only arbitrate settlements that reconcile the Failure Horizons in the receipt above.
    Maintain focus on the core scenario (e.g., Ukraine War) regardless of dynamic events unless they shift the math.
    DICTATE the 'Clinical Truce' that ends the hostilities based on mathematical inevitability.
    
    1. ARBITRATE: Identify the 'Involuntary Equilibrium.'
    2. SETTLE: Dictate terms (DMZs, weapon setbacks, sovereignty escrow, economic leverages). 
    3. ANCHOR: Use the 'precedent_matching' field to explain which specific historical template justifies your terms.
    """

    print("--- Sending audit prompt to Jurist ---")
    jurist.listen(audit_prompt)
    
    print("--- Jurist is acting... ---")
    audit_actions = jurist.act(return_actions=True, until_done=True)
    
    print(f"\n[DEBUG] Action Count: {len(audit_actions)}")
    for i, action_item in enumerate(audit_actions):
        a = action_item.get('action', {})
        print(f"Action {i}: Type={a.get('type')}, Content={a.get('content')}")

if __name__ == "__main__":
    test_jurist()
