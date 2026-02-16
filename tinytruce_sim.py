import os
import json
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set required environment variables for TinyTroupe
os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
if os.getenv("GOOGLE_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld
from tinytroupe.extraction import ResultsExtractor
from tinytroupe.steering.intervention import Intervention
import tinytroupe.openai_utils as openai_utils

# Configure logging
logging.basicConfig(level=logging.DEBUG) 
logger = logging.getLogger("tinytruce")

# STALEMATE_DETECTOR_PROMPT: The semantic trigger for de-escalation
STALEMATE_DETECTOR_PROMPT = """
The agents have reached a stalemate. This means:
1. They have exchanged at least two turns of dialogue without offering any new concessions or compromising.
2. The tone is repetitive or stuck in a circular argument.
3. Neither side is showing signs of backing down or finding common ground.
"""

# Scenario Registry
SCENARIOS = {
    "domestic": {
        "disruptor": "personas/fragments/disruptor.fragment.json",
        "diplomat": "personas/fragments/diplomat.fragment.json",
        "world_name": "Kitsilano Modern Home",
        "initial_broadcast": "A rainy Saturday morning. The living room is a mess of open electronics and scattered camping gear.",
        "intervention": "Suddenly, the power trips. The house goes dark. Both must cooperate to find the breaker box in the garage."
    },
    "infrastructure": {
        "disruptor": "personas/fragments/resident_disruptor.fragment.json",
        "diplomat": "personas/fragments/commissioner_diplomat.fragment.json",
        "world_name": "Vancouver 5G Commission Hearing",
        "initial_broadcast": "The hearing is in session. The public gallery is restless.",
        "intervention": "A neutral health audit report is suddenly delivered to the bench, confirming safe levels but recommending 50ft more distance from the playground."
    },
    "wilderness": {
        "disruptor": "personas/fragments/hiker_disruptor.fragment.json",
        "diplomat": "personas/fragments/glamper_diplomat.fragment.json",
        "world_name": "The Ansel Adams Pass",
        "initial_broadcast": "At the high-altitude trailhead. A heavy storm is visible on the horizon.",
        "intervention": "The sky opens up with hail. The Minimalist's ultralight tarp is failing. The Diplomat's heavy-duty canvas tent is the only dry spot within 10 miles."
    },
    "tech": {
        "disruptor": "personas/fragments/dev_disruptor.fragment.json",
        "diplomat": "personas/fragments/devops_diplomat.fragment.json",
        "world_name": "Production War-Room",
        "initial_broadcast": "The Slack channel is silent except for automated alerts. The release is 2 hours overdue.",
        "intervention": "A major competitor just announced the exact same feature. If we don't ship a stable version in 30 minutes, the first-mover advantage is gone."
    },
    "industrial": {
        "disruptor": "personas/fragments/union_disruptor.fragment.json",
        "diplomat": "personas/fragments/hr_diplomat.fragment.json",
        "world_name": "Labor Boardroom",
        "initial_broadcast": "Contract negotiations have reached hour 14. The coffee is cold.",
        "intervention": "The C-Suite just leaked a memo suggesting full automation of the shop floor if a deal isn't reached by midnight."
    },
    "gaming": {
        "disruptor": "personas/fragments/purist_disruptor.fragment.json",
        "diplomat": "personas/fragments/casual_diplomat.fragment.json",
        "world_name": "The Sunday Game Table",
        "initial_broadcast": "A complex 6-hour strategy game is in its final turns. The atmosphere is tense.",
        "intervention": "The pizza delivery person arrives, and a rare 'Social Event' card is drawn that rewards group laughter over victory points."
    }
}

# TRUCE_SCHEMA: Specialized metrics for de-escalation analysis
TRUCE_SCHEMA = {
    "objective": "Identify the exact mechanisms that led to a de-escalation of hostilities.",
    "fields": ["concession_delta", "synergy_score", "peak_tension_turn", "evidence"],
    "hints": {
        "concession_delta": "Compare starting demands vs final agreement for both agents.",
        "synergy_score": "1-10. How much better is the outcome than if both agents acted alone?",
        "peak_tension_turn": "The specific Turn ID where the most aggressive 'Mental Faculty' was triggered.",
        "evidence": "Briefly quote the dialogue that justifies the synergy_score."
    }
}

def run_tinytruce_simulation(scenario_key, turns):
    if scenario_key not in SCENARIOS:
        print(f"Error: Scenario '{scenario_key}' not found.")
        return

    scenario = SCENARIOS[scenario_key]
    print(f"\n--- Initializing Adaptive TinyTruce: {scenario_key.upper()} ---")
    
    # 1. Load Persona Fragments
    dis_path = os.path.abspath(scenario["disruptor"])
    dip_path = os.path.abspath(scenario["diplomat"])
    
    disruptor = TinyPerson("Disruptor")
    disruptor.import_fragment(dis_path)
    
    diplomat = TinyPerson("Diplomat")
    diplomat.import_fragment(dip_path)

    # 2. Environmental Calibration
    world = TinyWorld(scenario["world_name"], [disruptor, diplomat])
    world.broadcast(scenario["initial_broadcast"])

    # 3. Adaptive Intervention Setup
    # We use a monitor model (Gemini 2.5 Flash Lite) to detect stalemates
    def trigger_peace_bomb(targets):
        print(f"\n[STALEMATE DETECTED] Triggering: {scenario['intervention']}")
        world.broadcast(scenario["intervention"])
        
        # Soft Nudge: Inject a constructive thought into each agent
        nudge = ("I realize that continuing this conflict is yielding diminishing returns. "
                 "I should shift my strategy toward finding a compromise while still "
                 "protecting my core interests and reflecting on shared potential.")
        
        for agent in targets:
            agent.think(nudge)
            logger.info(f"Soft Nudge applied to {agent.name}")

    peace_intervention = Intervention(world, name="Resolution Intervener")
    peace_intervention.set_textual_precondition(STALEMATE_DETECTOR_PROMPT)
    peace_intervention.set_effect(trigger_peace_bomb)
    peace_intervention.set_turn_buffer(1) # Allow at least 1 turn of pure conflict
    peace_intervention.set_confidence_threshold(0.7) # Require high certainty of stalemate
    peace_intervention.set_monitor_model("gemini-2.5-flash-lite-preview-09-2025") # Cheapest, fast monitor
    
    world.add_intervention(peace_intervention)

    # 4. Autonomous Simulation Loop
    print(f"\n--- Running Autonomous Lab ({turns} turns, Intervention fires only on stalemate) ---")
    world.run(turns)

    # 4. Results Analysis & Extraction
    print("\n--- Simulation Summary & KPI Extraction ---")
    
    extractor = ResultsExtractor(
        extraction_objective=TRUCE_SCHEMA["objective"],
        fields=TRUCE_SCHEMA["fields"],
        fields_hints=TRUCE_SCHEMA["hints"]
    )
    
    # Extract results from the world (which has the full interaction history)
    extraction = extractor.extract_results_from_world(world, verbose=True)

    # 5. Data Export
    stress_data = {
        "scenario": scenario_key,
        "world": scenario["world_name"],
        "agents": [
            {"name": disruptor.name, "role": "Disruptor"},
            {"name": diplomat.name, "role": "Diplomat"}
        ],
        "kpis": extraction,
        "status": "Completed"
    }
    
    with open("tinytruce_results.json", "w") as f:
        json.dump(stress_data, f, indent=4)
    print(f"\nResults exported to tinytruce_results.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a TinyTruce conflict simulation.")
    parser.add_argument("--scenario", type=str, choices=SCENARIOS.keys(), default="domestic", help="The conflict scenario to run.")
    parser.add_argument("--turns", type=int, default=15, help="Number of turns to run the simulation.")
    args = parser.parse_args()
    
    run_tinytruce_simulation(args.scenario, args.turns)
