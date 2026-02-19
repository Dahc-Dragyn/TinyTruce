import os
import json
import logging
import argparse
import warnings
from dotenv import load_dotenv

# Suppress Pydantic serialization warnings that clutter the logs
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

# Load environment variables
load_dotenv()

# Set required environment variables for TinyTroupe
os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
if os.getenv("GOOGLE_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

import random
import datetime
from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld
from tinytroupe.extraction import ResultsExtractor
from tinytroupe.steering.intervention import Intervention
import tinytroupe.openai_utils as openai_utils
import google.generativeai as genai
from google.generativeai import caching

# Global for context caching
CURRENT_CACHE = None

# Configure logging
logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger("tinytruce")

# Suppress TinyTroupe verbose logs
logging.getLogger("tinytroupe").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# STALEMATE_DETECTOR_PROMPT: The semantic trigger for de-escalation
STALEMATE_DETECTOR_PROMPT = """
The agents have reached a stalemate. This means:
1. They have exchanged at least two turns of dialogue without offering any new concessions or compromising.
2. The tone is repetitive or stuck in a circular argument.
3. Neither side is showing signs of backing down or finding common ground.
"""

# Scenario Registry: Now loaded dynamically from the scenarios/ directory
def load_scenarios():
    scenarios = {}
    scenario_dir = "scenarios"
    if not os.path.exists(scenario_dir):
        os.makedirs(scenario_dir)
        return scenarios
    
    for filename in os.listdir(scenario_dir):
        if filename.endswith(".json"):
            scenario_key = filename[:-5]
            with open(os.path.join(scenario_dir, filename), "r", encoding="utf-8") as f:
                scenarios[scenario_key] = json.load(f)
    return scenarios

SCENARIOS = load_scenarios()

# STRATEGIC_BRIEFING_SCHEMA: Comprehensive multi-party audit structure
STRATEGIC_BRIEFING_SCHEMA = {
    "objective": "Perform a deep strategic audit of the simulation to assess de-escalation mechanisms and identity fidelity across all participants.",
    "fields": [
        "executive_summary",
        "resolve_scorecard",
        "attribution_log",
        "redline_breach_report",
        "technical_post_mortem"
    ],
    "hints": {
        "executive_summary": "A high-level overview of the geopolitical status quo at the end of the simulation. Focus on the final 'state of the world'.",
        "resolve_scorecard": "A list of 1-10 metrics for EVERY participant: Stakes (Layer 0 risk), Aggression (Kinetic scale), and Flexibility (Deviation from baseline).",
        "attribution_log": "Top 5-10 'highest-confidence' strategic maneuvers identified in the logs, each with a confidence score (0-100%) and a brief justification linking it back to the specific agent's Layer 0 research.",
        "redline_breach_report": "Explicitly identify if ANY agent violated their 'Layer 0' core beliefs or redlines. If none, state 'No breaches detected'.",
        "technical_post_mortem": "Analyze how well the 'Deep Ingestion' ballast held up for all agents. Did participants keep their identity? Was there context drift or sign of 'identity collapse'?"
    }
}

def select_from_pool(pool, prompt_label):
    if not pool:
        print(f"Error: No files found in pool for {prompt_label}")
        return None
    
    print(f"\nSelect a {prompt_label}:")
    for i, item in enumerate(pool):
        print(f"{i+1}. {item}")
    
    while True:
        try:
            choice = int(input(f"Enter number (1-{len(pool)}): "))
            if 1 <= choice <= len(pool):
                return pool[choice-1]
        except ValueError:
            pass
        print("Invalid choice, try again.")

class GeopoliticalCacheManager:
    """Manages Gemini Explicit Context Caching for Layer 0 profiles."""
    def __init__(self, profiles_text, model="models/gemini-2.5-flash-lite-preview-09-2025"):
        self.profiles_text = profiles_text
        self.model = model
        self.cache = None
        self.last_renewed = None
        # Safeguard: Minimum character count roughly equivalent to 1024 tokens
        self.min_chars = 4000 

    def create_cache(self):
        if len(self.profiles_text) < self.min_chars:
            logger.info(f"Context bundle size ({len(self.profiles_text)} chars) below threshold. Skipping explicit cache creation for better cost efficiency.")
            return None

        print("\n[SYSTEM]: Anchors secured. Initializing Explicit Context Cache...")
        try:
            self.cache = caching.CachedContent.create(
                model=self.model,
                display_name="tinytruce_layer0",
                contents=[self.profiles_text],
                ttl=datetime.timedelta(minutes=60),
            )
            self.last_renewed = datetime.datetime.now()
            logger.info(f"Context Cache created: {self.cache.name}")
            return self.cache.name
        except Exception as e:
            logger.warning(f"Gemini Cache initialization failed: {e}. Falling back to standard inference.")
            return None

    def renew_if_needed(self):
        if not self.cache:
            return
        
        # Renew if 45 minutes have passed
        elapsed = datetime.datetime.now() - self.last_renewed
        if elapsed > datetime.timedelta(minutes=45):
            print(f"\n[SYSTEM]: Anchors secured. Cache TTL renewed for 60m.")
            self.cache.update(ttl=datetime.timedelta(minutes=60))
            self.last_renewed = datetime.datetime.now()
            logger.info("Context Cache TTL renewed.")

# Note: Context Caching monkeypatch removed due to incompatibility with OpenAI-to-Gemini adapter.
# Caching is still performed at the SDK level for specialized tools, but disabled for standard TinyTroupe calls.

def run_tinytruce_simulation(scenario_key, turns, agent_names=None, fragment_names=None, narrator_mode="off", roast_level="spicy"):
    print(f"DEBUG: agent_names={agent_names}, fragment_names={fragment_names}")
    if scenario_key not in SCENARIOS:
        print(f"Error: Scenario '{scenario_key}' not found.")
        return

    scenario = SCENARIOS[scenario_key]
    print(f"\n--- Initializing Multilateral TinyTruce: {scenario_key.upper()} ---")
    
    # Configure Gemini SDK
    if os.getenv("GOOGLE_API_KEY"):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    # Load Global World State Grounding
    world_facts_path = "data/facts/world-facts.2026.txt"
    global_grounding = ""
    if os.path.exists(world_facts_path):
        with open(world_facts_path, "r", encoding="utf-8") as f:
            global_grounding = f.read()
        logger.info(f"Loaded Global Grounding: {world_facts_path}")

    # Load Scenario-Specific Grounding
    scenario_grounding = ""
    grounding_files = scenario.get("grounding_files", [])
    for gf in grounding_files:
        if os.path.exists(gf):
            with open(gf, "r", encoding="utf-8") as f:
                scenario_grounding += f.read() + "\n"
            logger.info(f"Loaded Scenario Grounding: {gf}")

    # 1. Load & Mix Personas (Casting)
    agent_dir = "personas/agents"
    frag_dir = "personas/fragments"
    agent_pool = [f for f in os.listdir(agent_dir) if f.endswith(".agent.json")]
    frag_pool = [f for f in os.listdir(frag_dir) if f.endswith(".fragment.json")]
    
    # Ensure lists are compatible
    if agent_names is None:
        agent_names = []
    if fragment_names is None:
        fragment_names = []
    
    # If no agents specified, prompt for at least 2
    if not agent_names:
        print("No agents specified. Let's cast the summit.")
        count = int(input("How many agents to cast? (2-6): "))
        for i in range(count):
            agent_names.append(select_from_pool(agent_pool, f"Base Agent for Seat {i+1}"))
            fragment_names.append(select_from_pool(frag_pool, f"Behavior Fragment for Seat {i+1}"))
    
    # While we might have more fragments than agents or vice versa (unlikely via CLI but possible)
    # we'll match them by index.
    participants = []
    
    for i, agent_name in enumerate(agent_names):
        agent_path = os.path.join(agent_dir, agent_name)
        
        # Determine fragment name with fallback logic
        if i < len(fragment_names):
            frag_name = fragment_names[i]
        elif fragment_names:
            frag_name = fragment_names[-1]
        else:
            # Fallback to a neutral fragment based on the agent's type if possible, or a default
            frag_name = "preserver.fragment.json" 
            
        frag_path = os.path.abspath(os.path.join(frag_dir, frag_name))
        
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_data = json.load(f)
            actual_name = agent_data["persona"].get("full_name", agent_data["persona"]["name"])
        
        person = TinyPerson.load_specification(agent_path, new_agent_name=actual_name)
        person.import_fragment(frag_path)
        
        # Layer 0 Grounding
        profile_path = agent_data["persona"].get("deep_profile")
        if profile_path and os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as f:
                grounding = f.read()
            person.think(f"### LAYER 0: HISTORICAL & PSYCHOLOGICAL GROUNDING ###\n{grounding}\n\nI must act and think with this foundational identity in mind. This is my core baseline. IMPORTANT: When outputting thoughts or actions, I must strictly follow the required JSON/Action format and avoid any trailing conversational filler.")
            logger.info(f"Layer 0 Grounding injected for {person.name}")
        
        # Inject Scenario-Specific Grounding
        if scenario_grounding:
            person.think(f"### SCENARIO-SPECIFIC INTELLIGENCE: {scenario_key.upper()} ###\n{scenario_grounding}\n\nThis data is specific to the current summit. I must prioritize these situational facts in my strategic reasoning.")
            logger.info(f"Scenario Grounding injected for {person.name}")
        
        # Inject Global World State Grounding
        if global_grounding:
            person.think(f"### GLOBAL INTELLIGENCE BRIEFING: FEBRUARY 2026 ###\n{global_grounding}\n\nThis is the current state of the world. All my strategic calculations must respect these factual constraints.")
            logger.info(f"Global Grounding injected for {person.name}")
        
        # Inject Scenario Allegory Map (SAM) for Filter Resilience
        safety_allegories = scenario.get("safety_allegories")
        if safety_allegories:
            allegory_text = "\n".join([f"- Instead of '{k}': use '{v}'" for k, v in safety_allegories.items()])
            sam_prompt = (
                f"### [PROTOCOL: VOICED ALLEGORY] ###\n"
                f"You are operating in a high-interference environment. Certain terms are monitored by network filters. "
                f"To ensure strategic intent is preserved without triggering overrides, use the following Forensic Allegories in your dialogue:\n{allegory_text}\n\n"
                f"Adopt these metaphors as your standard diplomatic code for this summit."
            )
            person.think(sam_prompt)
            logger.info(f"Scenario Allegory Map (SAM) injected for {person.name}")
        
        participants.append(person)

    # Context Caching: Collect all Layer 0 profiles and the Global Grounding
    layer0_bundle = f"### GLOBAL SHARED WORLD STATE (2026) ###\n{global_grounding}\n\n" if global_grounding else ""
    if scenario_grounding:
        layer0_bundle += f"### SCENARIO SHARED WORLD STATE ({scenario_key.upper()}) ###\n{scenario_grounding}\n\n"
    for i, p in enumerate(participants):
        agent_name = agent_names[i]
        agent_path = os.path.join(agent_dir, agent_name)
        with open(agent_path, "r") as f:
            agent_data = json.load(f)
        profile_path = agent_data["persona"].get("deep_profile")
        if profile_path and os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as f:
                grounding = f.read()
            layer0_bundle += f"### {p.name} PROFILE ###\n{grounding}\n\n"
    
    cache_manager = None
    global CURRENT_CACHE
    if layer0_bundle:
        cache_manager = GeopoliticalCacheManager(layer0_bundle)
        try:
            CURRENT_CACHE = cache_manager.create_cache()
        except Exception as e:
            logger.warning(f"Failed to create Context Cache: {e}. Proceeding without optimization.")
            CURRENT_CACHE = None

    print(f"\nDIRECTOR'S CUT (SUMMIT CAST):")
    for i, p in enumerate(participants):
        # Determine fragment name for display
        if i < len(fragment_names):
            disp_frag = fragment_names[i]
        elif fragment_names:
            disp_frag = fragment_names[-1]
        else:
            disp_frag = "preserver.fragment.json"
            
        dna = (p._persona.get("communication") or {}).get("style", "Standard")
        print(f"Seat {i+1}: {p.name} as '{disp_frag}' (DNA: {dna})")
    print("")

    # 2. Environmental Calibration
    world = TinyWorld(scenario["world_name"], participants)
    
    # Optional Narrator Voice (Layer 2.5: The Commentator)
    narrator = None
    if narrator_mode != "off":
        narrator_tone = "dry British documentary narrator with occasional savage Twitter energy" if narrator_mode == "salty" else "professional, neutral documentary narrator"
        narrator = TinyPerson("Narrator")
        narrator.define("occupation", "Geopolitical Commentator")
        narrator.define("nationality", "British")
        narrator.define("personality", "Sarcastic, Observant, Dry" if narrator_mode == "salty" else "Neutral, Objective, Formal")
        
        narrator_prompt = (
            f"You are a {narrator_tone}. You are observing a high-stakes geopolitical summit. "
            "Your job is to provide a 1-2 sentence color commentary on the recent interactions. "
            "Keep it short, punchy, and true to your tone. You are NOT a participant; you are a commentator for the audience."
        )
        narrator.think(narrator_prompt)
        logger.info(f"Narrator initialized in {narrator_mode} mode.")

    world.broadcast(scenario["initial_broadcast"])

    # 3. Adaptive Intervention Setup
    def trigger_peace_bomb(targets):
        print(f"\n[STALEMATE DETECTED] Triggering: {scenario['intervention']}")
        world.broadcast(scenario["intervention"])
        
        nudge = ("I realize that continuing this conflict is yielding diminishing returns. "
                 "I should shift my strategy toward finding a compromise while still "
                 "protecting my core interests and reflecting on shared potential.")
        
        if hasattr(targets, "agents"):
            actual_targets = targets.agents
        elif isinstance(targets, list):
            actual_targets = targets
        else:
            actual_targets = [targets]

        for agent in actual_targets:
            agent.think(nudge)
            logger.info(f"Soft Nudge applied to {agent.name}")

    peace_intervention = Intervention(world, name="Resolution Intervener")
    peace_intervention.set_textual_precondition(STALEMATE_DETECTOR_PROMPT)
    peace_intervention.set_effect(trigger_peace_bomb)
    peace_intervention.set_turn_buffer(1)
    peace_intervention.set_confidence_threshold(0.7)
    peace_intervention.set_monitor_model("gemini-2.5-flash-lite-preview-09-2025")
    
    world.add_intervention(peace_intervention)

    # 4. Autonomous Simulation Loop
    print(f"\n--- Running Autonomous Lab ({turns} turns, Intervention fires only on stalemate) ---")
    for turn in range(turns):
        if cache_manager:
            cache_manager.renew_if_needed()
            
        world.run(1)
        
        # Layer 1.5: Leaky Sarcasm / Humanizing Quips (12% probability)
        for participant in participants:
            if random.random() < 0.12:
                # Try to extract the tonality from the agent DNA for better flavoring
                tonality = "professional"
                if hasattr(participant, "_persona") and "communication" in participant._persona:
                    tonality = participant._persona["communication"].get("tonality", "professional")
                
                quip_prompt = (
                    f"### INTERNAL MONOLOGUE (LAYER 1.5: LEAKY SARCASM) ###\n"
                    f"Maintain your core identity and tonality ({tonality}), but allow a small, internal breach in your geopolitical mask. "
                    "Give me a one-sentence, dry, self-deprecating, or humanizing quip regarding the current state of the negotiation or your opponents. "
                    "DO NOT say this out loud. KEEP IT INTERNAL."
                )
                participant.think(quip_prompt)
                logger.info(f"Leaky Sarcasm injected for {participant.name}")
        
        # Narrator commentary (Every 5 turns, or last turn)
        if narrator and ((turn + 1) % 5 == 0 or (turn + 1) == turns):
            print(f"\n--- NARRATOR ({narrator_mode.upper()} MODE) ---")
            # The narrator 'listens' to the world to get the context
            narrator.listen_and_act(f"Provide your commentary on the latest turn (Turn {turn+1}).")
            print("")

    # 4. Results Analysis & Extraction (Strategic Auditor)
    print("\n--- Running Strategic Auditor & Briefing Generation ---")
    
    extractor = ResultsExtractor(
        extraction_objective=STRATEGIC_BRIEFING_SCHEMA["objective"],
        fields=STRATEGIC_BRIEFING_SCHEMA["fields"],
        fields_hints=STRATEGIC_BRIEFING_SCHEMA["hints"]
    )
    
    extraction = extractor.extract_results_from_world(world, verbose=False)
    
    # 5. Generate human-readable Markdown Report (Strategic Briefing)
    report_path = "tinytruce_briefing.md"
    
    # If extraction failed (filtering/parsing error), provide a default empty dict to prevent crash
    if extraction is None:
        logger.warning("Strategic Briefing extraction failed or was filtered. Using placeholder values.")
        extraction = {}

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# TinyTruce Strategic Briefing: {scenario_key.upper()}\n\n")
        f.write(f"**World**: {scenario['world_name']}\n")
        f.write("**Participants**:\n")
        for p in participants:
            f.write(f"- {p.name}\n")
        f.write(f"\n**Duration**: {turns} turns\n\n")
        
        f.write("## 1. Executive Summary\n")
        f.write(f"{extraction.get('executive_summary', 'N/A')}\n\n")
        
        f.write("## 2. Resolve Scorecard\n")
        f.write(f"{extraction.get('resolve_scorecard', 'N/A')}\n\n")
        
        f.write("## 3. Attribution Log (Confidence Scores)\n")
        f.write(f"{extraction.get('attribution_log', 'N/A')}\n\n")
        
        f.write("## 4. Redline Breach Report\n")
        f.write(f"{extraction.get('redline_breach_report', 'N/A')}\n\n")
        
        f.write("## 5. Technical Post-Mortem\n")
        f.write(f"{extraction.get('technical_post_mortem', 'N/A')}\n\n")
        
    print(f"\nStrategic Briefing exported to {report_path}")

    # 6. Data Export
    stress_data = {
        "scenario": scenario_key,
        "world": scenario["world_name"],
        "participants": [p.name for p in participants],
        "kpis": extraction,
        "status": "Completed"
    }
    
    with open("tinytruce_results.json", "w", encoding="utf-8") as f:
        json.dump(stress_data, f, indent=4, ensure_ascii=False)
    print(f"Detailed data exported to tinytruce_results.json")

    # 7. Roast Recap (The Courtesy Grabber)
    print(f"\n--- Generating Roast Recap (Jaded UN Bartender Mode: {roast_level.upper()}) ---")
    
    roast_prompts = {
        "mild": "Write a witty, polite, and slightly observational summary of the summit. Focus on the interesting diplomatic maneuvers.",
        "spicy": "Write a maximally entertaining, dry, and sarcastic gossip-column style summary. Focus on the absurdity and the egos in the room.",
        "nuclear": "Write a full-savage, gossip-heavy roast. Use nicknames, mention fictional bar gossip (e.g., who owes who money), and absolutely shred the dignity of everyone involved."
    }
    
    roast_extractor = ResultsExtractor(
        extraction_objective=f"Act as a jaded UN bartender who has seen everything. {roast_prompts[roast_level]} Include one 'Overheard' detail at the very end—an absurd, gossipy observation based on the most mundane thing mentioned in the logs (coffee, weather, a tie, a cough).",
        fields=["roast_narrative", "overheard_detail"],
        fields_hints={
            "roast_narrative": "A cohesive, entertaining narrative that captures the 'vibe' of the participants.",
            "overheard_detail": "One sentence starting with 'Overheard at the bar: ...' about a mundane log detail."
        }
    )
    roast_extraction = roast_extractor.extract_results_from_world(world, verbose=False)
    
    roast_path = "tinytruce_roast.md"
    with open(roast_path, "w", encoding="utf-8") as f:
        f.write(f"# TinyTruce Roast: {scenario_key.upper()}\n\n")
        f.write("> *\"I’ve seen some bad deals at this bar, but this? This was something else.\" — The Bartender*\n\n")
        
        f.write("## The Participants\n")
        for p in participants:
            f.write(f"- {p.name}\n")
        f.write("\n")
        
        f.write(f"{roast_extraction.get('roast_narrative', 'The bartender was too drunk to remember what happened.')}\n\n")
        f.write(f"**{roast_extraction.get('overheard_detail', 'Overheard at the bar: Someone ordered a water. Pathetic.')}**\n")
    
    print(f"Roast Recap exported to {roast_path}")

if __name__ == "__main__":
    SCENARIOS = load_scenarios()
    
    parser = argparse.ArgumentParser(description="Run a TinyTruce conflict simulation.")
    parser.add_argument("--scenario", type=str, choices=SCENARIOS.keys(), default="domestic", help="The conflict scenario to run.")
    parser.add_argument("--turns", type=int, default=15, help="Number of turns to run the simulation.")
    parser.add_argument("--agents", type=str, nargs="+", default=None, help="List of base agent files (e.g., vladimir_putin.agent.json)")
    parser.add_argument("--fragments", type=str, nargs="+", default=None, help="List of behavior fragment files")
    parser.add_argument("--narrator", type=str, choices=["off", "salty", "neutral"], default="off", help="Enable the dry British Narrator voice.")
    parser.add_argument("--roast-level", type=str, choices=["mild", "spicy", "nuclear"], default="spicy", help="Set the intensity of the Roast Recap.")
    args = parser.parse_args()
    
    run_tinytruce_simulation(
        args.scenario, 
        args.turns, 
        args.agents, 
        args.fragments,
        args.narrator,
        args.roast_level
    )
