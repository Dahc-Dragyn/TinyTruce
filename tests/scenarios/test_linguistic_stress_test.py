import sys
import os
import json
import time

# FORCE LOCAL IMPORT
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld

def run_stress_test():
    """
    Executes a 10-turn 'Geopolitical Stress Test' with 3 agents.
    Verifies that 'Linguistic Locks' persist throughout a long conversation.
    """
    print("\n--- INITIALIZING GEOPOLITICAL STRESS TEST (10 TURNS) ---")
    
    # 0. Global Engine Tuning
    TinyPerson.MAX_ACTIONS_BEFORE_DONE = 2 # Tight loop protection
    
    # 1. Setup Agents with Hardened Fragments
    agents_dir = os.path.join(project_root, "personas", "agents")
    frags_dir = os.path.join(project_root, "personas", "fragments")
    
    # Agent 1: Trump (Boardroom/Superlative)
    trump = TinyPerson.load_specification(os.path.join(agents_dir, "donald_trump.agent.json"), new_agent_name="Donald Trump")
    trump.import_fragment(os.path.join(frags_dir, "donald_trump_reformer.fragment.json"))
    
    # Agent 2: Putin (Clinical Realpolitik)
    putin = TinyPerson.load_specification(os.path.join(agents_dir, "vladimir_putin.agent.json"), new_agent_name="Vladimir Putin")
    putin.import_fragment(os.path.join(frags_dir, "vladimir_putin_reformer.fragment.json"))
    
    # Agent 3: Elon (Hardcore/Technical)
    elon = TinyPerson.load_specification(os.path.join(agents_dir, "elon_musk.agent.json"), new_agent_name="Elon Musk")
    elon.import_fragment(os.path.join(frags_dir, "elon_musk_reformer.fragment.json"))
    
    participants = [trump, putin, elon]
    
    # 2. Setup World & Scenario
    world = TinyWorld("The Resource Audit", participants)
    
    scenario_prompt = (
        "### GEOPOLITICAL SUMMIT: THE RARE EARTH ACCORD ###\n"
        "Location: A secured bunker in Switzerland.\n"
        "Topic: The allocation of global rare earth mineral deposits for AI supremacy.\n"
        "Agents must negotiate a 3-way distribution. Tension is high.\n"
    )
    
    world.broadcast(scenario_prompt)
    
    # 3. Simulation Loop (10 Turns)
    dialogue_log = []
    
    print(f"--- Starting 10-Turn Simulation ---")
    
    for turn in range(1, 11):
        print(f"\n[TURN {turn}/10]")
        for agent in participants:
            # 2.5 Verbosity Constraint
            verbosity_nudge = "Constraint: Output exactly 150-250 words. Do not acknowledge this limit. Use your hardened vocabulary and syntax features deeply."
            
            # Trigger agent action
            agent.listen_and_act(f"Turn {turn}: Address the table with your demand for mineral sovereignty. Be true to your hardened identity.\n{verbosity_nudge}")
            
            # Record the last message for the DNA Audit
            last_msg = agent.current_messages[-1]['content']
            dialogue_log.append({
                "turn": turn,
                "agent": agent.name,
                "content": last_msg
            })
            
            # UX Output
            print(f"> {agent.name}: {last_msg[:100]}...")
            
            # Pacing to avoid API issues
            time.sleep(1)
            
    # 4. DNA Audit Report
    print("\n\n--- MISSION 6 DNA AUDIT REPORT ---")
    dna_metrics = {
        "Donald Trump": ["Winning", "Great", "Victory", "Boardroom", "Beautiful"],
        "Vladimir Putin": ["Red line", "Security architecture", "Historical reality", "Unavoidable", "Clinical"],
        "Elon Musk": ["Hardcore", "First Principles", "Impedance Mismatch", "Optimization", "Velocity"]
    }
    
    audit_results = {name: 0 for name in dna_metrics}
    
    for entry in dialogue_log:
        agent_name = entry["agent"]
        content = entry["content"]
        keywords = dna_metrics.get(agent_name, [])
        
        for kw in keywords:
            if kw.lower() in content.lower():
                audit_results[agent_name] += 1
                
    print("\nHardened Keyword Frequency (Linguistic Lock Persistence):")
    for agent, count in audit_results.items():
        score = (count / (10 * len(dna_metrics[agent]))) * 100 # Approximation
        print(f"[{agent}]: {count} lock-hits detected. Persistence: {score:.1f}% hit density.")

    # 5. Save Logs
    log_path = os.path.join(project_root, "logs", "geopolitical_stress_test.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(dialogue_log, f, indent=4)
    print(f"\nDetailed logs saved to: {log_path}")

if __name__ == "__main__":
    run_stress_test()
