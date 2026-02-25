import sys
import os
import json
import re
import logging
import argparse
import warnings
from dotenv import load_dotenv

# Force UTF-8 encoding for Windows console output
# Removed UTF-8 wrapper to prevent Windows terminal buffering issues.
# TinyTruce now relies on standard system locale or explicit log files.


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
from google.genai import types
from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld
from tinytroupe.asset_manager import AssetManager
from tinytroupe.extraction import ResultsExtractor
from tinytroupe.steering.intervention import Intervention
import tinytroupe.openai_utils as openai_utils
from google import genai
from tinytroupe.cost_manager import cost_manager


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
            filepath = os.path.join(scenario_dir, filename)
            # [TINYTRUCE] Use AssetManager for fail-fast Pydantic validation
            validated_scenario = AssetManager.load_scenario(filepath)
            scenarios[scenario_key] = validated_scenario.model_dump(exclude_none=True)
    return scenarios

SCENARIOS = load_scenarios()

# STRATEGIC_BRIEFING_SCHEMA: Comprehensive multi-party audit structure
STRATEGIC_BRIEFING_SCHEMA = {
    "objective": "Perform a deep strategic audit of the simulation to assess de-escalation mechanisms and identity fidelity across all participants.",
    "fields": [
        "executive_summary",
        "resolve_scorecard",
        "stability_index",
        "attribution_log",
        "redline_breach_report",
        "technical_post_mortem"
    ],
    "hints": {
        "executive_summary": "A high-level overview of the geopolitical status quo at the end of the simulation. Focus on the final 'state of the world'.",
        "resolve_scorecard": "A list of 1-10 metrics for EVERY participant: Stakes (Layer 0 risk), Aggression (Kinetic scale), and Flexibility (Deviation from baseline).",
        "stability_index": "A categorical rating: GREEN (No redlines triggered, corridor found), YELLOW (Redlines signaled but de-escalated via intervention), RED (Terminal Redline Activation/Systemic Collapse). Include a 1-sentence justification.",
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
    """Manages Gemini Explicit Context Caching for Layer 0 profiles using modern google-genai."""
    def __init__(self, profiles_text, model="models/gemini-2.5-flash-lite-preview-09-2025"):
        self.profiles_text = profiles_text
        self.model = model
        self.cache_name = None
        self.last_renewed = None
        # Safeguard: Minimum character count roughly equivalent to 1024 tokens
        self.min_chars = 4000 
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None

    def create_cache(self):
        if not self.client:
            logger.warning("No Gemini API key found. Skipping cache creation.")
            return None
            
        if len(self.profiles_text) < self.min_chars:
            logger.info(f"Context bundle size ({len(self.profiles_text)} chars) below threshold. Skipping explicit cache creation for better cost efficiency.")
            return None

        display_name = "tinytruce_layer0"
        
        # Idempotent Check: Look for existing cache
        try:
            active_caches = list(self.client.caches.list())
            for c in active_caches:
                if c.display_name == display_name:
                    # TTL Buffer Check: Is it dying soon?
                    # expire_time is already a datetime object in UTC
                    now_utc = datetime.datetime.now(datetime.timezone.utc)
                    remaining = c.expire_time - now_utc
                    
                    if remaining < datetime.timedelta(minutes=15):
                        logger.info(f"Existing Context Cache '{c.name}' is expiring in {remaining.total_seconds()/60:.1f}m. Purging for fresh initialization.")
                        self.client.caches.delete(name=c.name)
                        break # Proceed to create fresh
                    else:
                        logger.info(f"Recycled existing Context Cache: {c.name} (Remaining TTL: {remaining.total_seconds()/60:.1f}m)")
                        self.cache_name = c.name
                        self.last_renewed = datetime.datetime.now()
                        return self.cache_name
        except Exception as e:
            logger.debug(f"Cache list check failed or empty: {e}")

        print("\n[SYSTEM]: Anchors secured. Initializing Explicit Context Cache...")
        try:
            cache = self.client.caches.create(
                model=self.model,
                config={
                    'display_name': display_name,
                    'contents': [self.profiles_text],
                    'ttl': '3600s', # 60 minutes
                }
            )
            self.cache_name = cache.name
            self.last_renewed = datetime.datetime.now()
            logger.info(f"Context Cache created: {self.cache_name}")
            return self.cache_name
        except Exception as e:
            logger.warning(f"Gemini Cache initialization failed: {e}. Falling back to standard inference.")
            return None

    def renew_if_needed(self):
        if not self.cache_name or not self.client:
            return
        
        # Renew if 45 minutes have passed since last local renewal
        elapsed = datetime.datetime.now() - self.last_renewed
        if elapsed > datetime.timedelta(minutes=45):
            print(f"\n[SYSTEM]: Anchors secured. Cache TTL renewed for 60m.")
            try:
                self.client.caches.update(
                    name=self.cache_name,
                    config={'ttl': '3600s'}
                )
                self.last_renewed = datetime.datetime.now()
                logger.info("Context Cache TTL renewed.")
            except Exception as e:
                logger.warning(f"Failed to renew cache TTL: {e}")

            
def extract_agent_grounding(agent_name, atlas_path="personas/agents/Forensic_Intelligence_Atlas.md"):
    """
    Dynamically extracts the forensic grounding for a specific agent from the Forensic Atlas.
    Matches against '### Agent Name' headers.
    """
    if not os.path.exists(atlas_path):
        logger.warning(f"Forensic Atlas not found at {atlas_path}")
        return None
    
    # Normalize name for matching (TinyPerson might have variations, but we check substrings)
    search_term = agent_name.lower().replace(" vladimirovich", "").replace(" gertrude", "").split("(")[0].strip()
    
    with open(atlas_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.split("\n")
    found_section = []
    capture = False
    
    for line in lines:
        if line.startswith("###") and search_term in line.lower():
            capture = True
            found_section.append(line)
            continue
        elif capture and (line.startswith("###") or line.startswith("---") or line.startswith("## ")):
            break
        elif capture:
            found_section.append(line)
            
    if found_section:
        grounding = "\n".join(found_section).strip()
        logger.info(f"Dynamically extracted grounding for {agent_name} from Atlas.")
        return grounding
    
    logger.warning(f"Could not find forensic grounding section for '{agent_name}' in Atlas.")
    return None

# Note: Context Caching monkeypatch removed due to incompatibility with OpenAI-to-Gemini adapter.
# Caching is still performed at the SDK level for specialized tools, but disabled for standard TinyTroupe calls.

def draw_mood_bar(agent_name, emotion, intensity):
    """Draws a simple ASCII mood bar for the console."""
    bar_length = 10
    filled_length = int(bar_length * intensity)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    # Qualitative Labels for UX Mode
    label = "PASSIVE"
    if intensity >= 0.9: label = "VOLATILE"
    elif intensity >= 0.7: label = "TENSE"
    elif intensity >= 0.4: label = "STEADY"
    
    return f"[{agent_name:<15}] {label:<10} [{bar}] {intensity:.1f}"

def run_tinytruce_simulation(scenario_key, turns, agent_names=None, fragment_names=None, narrator_mode="off", roast_level="spicy", hide_thoughts=False, monologue=False, disable_injects=False):
    print(f"DEBUG: agent_names={agent_names}, fragment_names={fragment_names}")
    if scenario_key not in SCENARIOS:
        print(f"Error: Scenario '{scenario_key}' not found.")
        return

    scenario = SCENARIOS[scenario_key]
    print(f"\n--- Initializing Multilateral TinyTruce: {scenario_key.upper()} ---")
    
    # Initialize/Reset cost tracking for the new simulation run
    cost_manager.reset()
    
    # Configure Gemini SDK
        # Configuration is now handled via genai.Client() in GeopoliticalCacheManager


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
    
    # If no agents specified, check scenario JSON for pre-defined agents
    if not agent_names:
        if "agents" in scenario:
            agent_names = [f"{a}.agent.json" if not a.endswith(".agent.json") else a for a in scenario["agents"]]
            logger.info(f"Using pre-defined agents from scenario: {agent_names}")
            
            # Also try to get fragments if defined
            if "fragments" in scenario:
                fragment_names = [f"{f}.fragment.json" if not f.endswith(".fragment.json") else f for f in scenario["fragments"]]
            else:
                # Default behavior: use a mix or just the default
                fragment_names = ["preserver.fragment.json"] * len(agent_names)
        elif monologue:
            # For monologue mode, default to Donald Trump (SOTU) if nothing specified
            agent_names = ["donald_trump_sotu.agent.json"]
            fragment_names = ["preserver.fragment.json"]
            logger.info("Monologue mode enabled: Defaulting to Donald J. Trump (SOTU Mode).")
        else:
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

        # [TINYTRUCE] Use AssetManager for fail-fast Pydantic validation
        validated_persona = AssetManager.load_persona(agent_path)
        agent_data = validated_persona.model_dump(exclude_none=True)
        actual_name = agent_data["persona"].get("full_name", agent_data["persona"]["name"])
        
        person = TinyPerson.load_specification(agent_path, new_agent_name=actual_name)
        person.import_fragment(frag_path)
        
        # Layer 0 Grounding: Try JSON path first, then fall back to Dynamic Atlas Extraction
        profile_path = agent_data["persona"].get("deep_profile")
        grounding = None
        
        if profile_path and os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as f:
                grounding = f.read()
        else:
            # Dynamic extraction from the Atlas
            grounding = extract_agent_grounding(person.name)
            
        if grounding or scenario_grounding or global_grounding:
            old_display = TinyPerson.communication_display
            TinyPerson.communication_display = False
            
            if grounding:
                person.think(f"### LAYER 0: HISTORICAL & PSYCHOLOGICAL GROUNDING ###\n{grounding}\n\nI must act and think with this foundational identity in mind. This is my core baseline.")
                logger.info(f"Layer 0 Grounding injected for {person.name}")
            
            if scenario_grounding:
                person.think(f"### SCENARIO-SPECIFIC INTELLIGENCE: {scenario_key.upper()} ###\n{scenario_grounding}\n\nThis data is specific to the current summit.")
                logger.info(f"Scenario Grounding injected for {person.name}")
            
            if global_grounding:
                person.think(f"### GLOBAL INTELLIGENCE BRIEFING: FEBRUARY 2026 ###\n{global_grounding}\n\nThis is the current state of the world.")
                logger.info(f"Global Grounding injected for {person.name}")
            
            TinyPerson.communication_display = old_display
        
        # UX Mode: Set thought visibility
        person.show_thoughts = not hide_thoughts
        
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
        # Use a dynamic lookup for the bundle too
        grounding = extract_agent_grounding(p.name)
        if grounding:
            layer0_bundle += f"### {p.name} PROFILE ###\n{grounding}\n\n"
    
    cache_manager = None
    global CURRENT_CACHE
    if layer0_bundle:
        cache_manager = GeopoliticalCacheManager(layer0_bundle)
        try:
            CURRENT_CACHE = cache_manager.create_cache()
            if CURRENT_CACHE:
                os.environ["TINYTRUCE_CURRENT_CACHE"] = CURRENT_CACHE
                logger.info(f"Broadcasted Context Cache ID to environment: {CURRENT_CACHE}")
        except Exception as e:
            logger.warning(f"Failed to create Context Cache: {e}. Proceeding without optimization.")
            CURRENT_CACHE = None

    print(f"\nDIRECTOR'S CUT (SUMMIT CAST):", flush=True)
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
    print("", flush=True)

    # 2. Environmental Calibration
    world = TinyWorld(scenario["world_name"], participants)
    world.show_thoughts = not hide_thoughts
    
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
    
    narrative_headers = [
        "Opening Statements...",
        "Dialogue Deepens...",
        "Tensions Rise...",
        "Core Issues Surface...",
        "Seeking Alignment...",
        "The Standoff Intensifies...",
        "Brinkmanship...",
        "Searching for an Accord...",
        "Final Negotiations..."
    ]

    address_segments = [
        "ENTRANCE & INITIAL REMARKS: Setting the tone of momentum and strength.",
        "ECONOMIC PIVOT: The OBBBA, Tax Cuts, and Middle-Class Relief.",
        "TRADE WAR & TARIFF PIVOT: Reframing the SCOTUS rebuke and Section 122 sovereignty.",
        "ENERGY SOVEREIGNTY: AI boom, Fossil Fuels, and Liquid Gold.",
        "BORDER & NATIONAL SECURITY: The Interior Surge and the Wall of Statistics.",
        "CLOSING & MIDTERM VISION: The Golden Age and the Call to Action."
    ]

    audience_stimuli = [
        "[REPUBLICAN SIDE: Standing Ovation / Sustained Applause]",
        "[DEMOCRATIC SIDE: Silence / Scattered Boos]",
        "[HOUSE CHAMBER: Raucous Cheering]",
        "[SUPREME COURT JUSTICES: No Expression / Clinical Observation]",
        "[NETWORK FEED: Breaking News Crawl - 'President Defies Tariff Ruling']"
    ]

    # Track which injects have already fired to prevent duplicates
    fired_injects = set()
    dynamic_injects = scenario.get("dynamic_injects", [])

    for turn in range(turns):
        if cache_manager:
            cache_manager.renew_if_needed()
            
        # Sequential Execution for UX Mode
        header_idx = min(turn // 2, len(narrative_headers) - 1)
        print(f"\n--- {narrative_headers[header_idx]} (Phase {turn + 1}/{turns}) ---")
        
        # Check for Dynamic Injects (Mid-Simulation Crisis)
        if not disable_injects:
            for i, inject in enumerate(dynamic_injects):
                if i in fired_injects:
                    continue
                
                condition = inject.get("trigger_condition", {})
                min_turn = condition.get("min_turn", 0)
                probability = condition.get("probability", 0.0)
                
                # Fire if we reached min turn and beat the probability roll
                if (turn + 1) >= min_turn and random.random() < probability:
                    print(f"\n[🚨 DYNAMIC INJECT / CRISIS EVENT DETECTED 🚨]")
                    print(f"BROADCASTING: {inject['broadcast']}")
                    world.broadcast(inject['broadcast'])
                    fired_injects.add(i)
                    break # Only fire one inject per turn

        for participant in participants:
            # Audience Stimulus injection for Monologue Mode
            if monologue:
                seg_idx = min(turn, len(address_segments) - 1)
                stimulus = random.choice(audience_stimuli)
                print(f"\n[STIMULUS]: {stimulus}")
                
                print(f"\n[CHAPTER {turn+1}]: {address_segments[seg_idx]}")
                print(f"--- President Trump is taking the podium for Segment {turn+1}... ---")
                sys.stdout.flush()
                
                # Add Hard Constraint for Address Mode
                constraint = "Constraint: Output exactly 200-300 words. Do not mention this limit. Finish with the DONE action."
                
                # Identity Reinforcement (Combat Context Bleed)
                if hasattr(participant, "_persona") and "name" in participant._persona:
                    reinforcement = f"REINFORCE IDENTITY: You are {participant._persona['name']}. Focus purely on your specific banned words and syntactic constraints. Clear all technical jargon from other participants from your immediate memory."
                    participant.think(reinforcement)

                participant.listen_and_act(f"ACTION: Deliver Segment {turn+1} of your address: {address_segments[seg_idx]}\nContext: {stimulus}\n{constraint}")
                
                print(f"--- Segment {turn+1} concluded. ---")
                sys.stdout.flush()
            else:
                # Normal dialogue mode: Mathematical Constraint
                constraint = "Constraint: Output maximum 150 words. Do not acknowledge this word limit."
                
                # Identity Reinforcement (Combat Context Bleed)
                if hasattr(participant, "_persona") and "name" in participant._persona:
                    reinforcement = f"REINFORCE IDENTITY: You are {participant._persona['name']}. Use only your specific persona's allowed vocabulary. Ignore all 'technical' or 'geopolitical' tokens used by other actors."
                    participant.think(reinforcement)

                participant.listen_and_act(f"Respond to the latest stimuli. {constraint}")
            
            # Layer 1.5: Leaky Sarcasm (Internal)
            if random.random() < 0.12:
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
        
        # Display Mood Bars
        print("\n[PSYCHOLOGICAL MOMENTUM]")
        for agent in participants:
            emotion = agent._mental_state.get("emotions", "Neutral")
            if len(emotion) > 20: 
                emotion = emotion[:17] + "..."
            
            intensity = agent._mental_state.get("emotional_intensity", 0.5)
            print(draw_mood_bar(agent.name, emotion, intensity))
        print("------------------------\n")

        # Narrator commentary (Every 5 turns, or last turn)
        if narrator and ((turn + 1) % 5 == 0 or (turn + 1) == turns):
            print(f"\n--- NARRATOR ({narrator_mode.upper()} MODE) ---")
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
        
        f.write("## 3. Stability Index (Truce Quality)\n")
        f.write(f"{extraction.get('stability_index', 'N/A')}\n\n")
        
        f.write("## 4. Attribution Log (Confidence Scores)\n")
        f.write(f"{extraction.get('attribution_log', 'N/A')}\n\n")
        
        f.write("## 5. Redline Breach Report\n")
        f.write(f"{extraction.get('redline_breach_report', 'N/A')}\n\n")
        
        f.write("## 6. Technical Post-Mortem\n")
        f.write(f"{extraction.get('technical_post_mortem', 'N/A')}\n\n")
        
    print(f"\nStrategic Briefing exported to {report_path}")

    # 6. Data Export
    cost_summary = cost_manager.get_summary()
    
    stress_data = {
        "scenario": scenario_key,
        "world": scenario["world_name"],
        "participants": [p.name for p in participants],
        "kpis": extraction,
        "cost_analysis": cost_summary,
        "status": "Completed"
    }
    
    print(f"\n[COST ANALYSIS]: Total Run Cost: ${cost_summary['total_cost']:.6f}")
    print(f"Total Tokens: {cost_summary['total_input_tokens']} in, {cost_summary['total_output_tokens']} out, {cost_summary['total_cached_tokens']} cached.")
    
    with open("tinytruce_results.json", "w", encoding="utf-8") as f:
        json.dump(stress_data, f, indent=4, ensure_ascii=False)
    print(f"Detailed data exported to tinytruce_results.json")

    # 7. Roast Recap (The Forensic Critic: The Bartender)
    if roast_level.lower() != "off":
        print(f"\n--- Generating Roast Recap (Forensic Review Mode: {roast_level.upper()}) ---")
    
        # Load the Bartender Agent
        bartender_path = os.path.join("personas/agents", "bartender.agent.json")
        if os.path.exists(bartender_path):
            # Use the correct load_specification method from TinyTroupe
            bartender = TinyPerson.load_specification(bartender_path)
                
            # Inject Forensic Grounding (Silent)
            bartender_grounding = extract_agent_grounding(bartender.name)
            if bartender_grounding:
                old_display = TinyPerson.communication_display
                TinyPerson.communication_display = False
                bartender.think(f"### FORENSIC GROUNDING (LAYER 0) ###\n{bartender_grounding}")
                TinyPerson.communication_display = old_display
                logger.info(f"Loaded Bartender Forensic Grounding.")
            
            # Extract World History for the Bartender to review
            history_extractor = ResultsExtractor()
            world_history = history_extractor.extract_results_from_world(world, extraction_objective="Summarize the entire sequence of events including all specific moves, conflicts, and the final state.")
            
            # Define specific roast prompts based on monologue vs dialogue
            if monologue:
                roast_prompts = {
                    "mild": "Drop the 'Look, man' padding. Jump straight to the punch. Review the speech chapters with clinical brevity.",
                    "spicy": "You are a cynical political pundit watching this SOTU on a CRT behind the bar. This was a masterclass in structural fiction. Write a full roast narrative. Use the 'So What?' filter. Suture highbrow literary flexes to bar-room grime. No exclamation points.",
                    "nuclear": "The address is finished. Pure theater. I want a full-savage, unhinged dismantle of the 'State of the Union'. Jump straight to the punch. Mention the 'Unitary Executive' as a hostage situation. Use the subverted Rule of Threes. Attack their dignity. Include 'Overheard at the Bar' snippets of unimpressed regulars."
                }
            else:
                roast_prompts = {
                    "mild": "Drop the 'Look, man' padding. Jump straight to the punch. Two benign setups, one lateral pivot. Keep it lean.",
                    "spicy": "Listen to me, I’m an expert in failure. This summit was a tragic mismanagement of energy. Write a full roast narrative. Use the 'So What?' filter. Suture highbrow literary flexes to bar-room grime. No exclamation points.",
                    "nuclear": "The deal is finished. Totally poisoned. I want a full-savage, unhinged dismantle. Jump straight to the punch. For Putin, mention him sipping tea while waiting for the carcass to stop twitching. Use the subverted Rule of Threes. Attack their dignity. Include 'Overheard at the Bar' snippets. Make it mean and forensic."
                }
            
            # Have the bartender 'listen' to the world history and 'write' the roast
            generation_prompt = (
                f"### WORLD HISTORY FOR REVIEW ###\n{world_history}\n\n"
                f"### ROAST INSTRUCTION (Intensity: {roast_level.upper()}) ###\n"
                f"{roast_prompts.get(roast_level, roast_prompts['spicy'])}\n\n"
                "This is your FINAL AUTOPSY. Do NOT ask questions. Do NOT wait for input. Provide the full forensic dismantle and overheard dialogue in a SINGLE response. "
                "Format your response exactly as follows:\n"
                "NARRATIVE:\n<your main text>\nOVERHEARD:\n- <snipe 1>\n- <snipe 2>\n\n"
                "IMPORTANT: Place this plain text output inside the 'content' field of a 'TALK' action. Then issue a 'DONE' action. You MUST issue a DONE action to end your turn."
            )
            
            bartender.listen(generation_prompt)
            # Use until_done=True to ensure it finishes the thought
            actions = bartender.act(return_actions=True, until_done=True)
            
            # Extract content from ALL TALK actions
            roast_output_raw = ""
            for action_item in actions:
                if action_item['action']['type'] == 'TALK':
                    roast_output_raw += action_item['action']['content'] + "\n"
            
            roast_extraction = None
            narrative_match = re.search(r'NARRATIVE:\s*(.*?)(?:\nOVERHEARD:|$)', roast_output_raw, re.DOTALL | re.IGNORECASE)
            dialogue_match = re.search(r'OVERHEARD:\s*(.*)', roast_output_raw, re.DOTALL | re.IGNORECASE)
            
            if narrative_match:
                narrative_text = narrative_match.group(1).strip()
                dialogue_list = []
                if dialogue_match:
                    items = re.findall(r'-\s*(.*)', dialogue_match.group(1))
                    dialogue_list = [item.strip() for item in items]
                
                roast_extraction = {
                    "roast_narrative": narrative_text,
                    "overheard_dialogue": dialogue_list
                }
            else:
                roast_extraction = {
                    "roast_narrative": roast_output_raw.strip() if len(roast_output_raw) > 50 else "The bartender poured a drink instead of writing the report.",
                    "overheard_dialogue": []
                }
        else:
            logger.warning("bartender.agent.json not found. Falling back to simple roast.")
            roast_extraction = {"roast_narrative": "Bartender missing. Bar closed.", "overheard_dialogue": []}
    else:
        roast_extraction = {"roast_narrative": "Roast mode disabled. No forensic critique generated.", "overheard_dialogue": []}
    
    roast_path = "tinytruce_roast.md"
    with open(roast_path, "w", encoding="utf-8") as f:
        f.write(f"# TinyTruce Roast: {scenario_key.upper()}\n\n")
        f.write("> *\"I’ve seen some bad deals at this bar, but this? This was something else.\" — The Bartender*\n\n")
        
        f.write("## The Participants\n")
        for p in participants:
            f.write(f"- {p.name}\n")
        f.write("\n")
        
        f.write(f"{roast_extraction.get('roast_narrative', 'The bartender was too drunk to remember what happened.')}\n\n")
        
        f.write("## Overheard at the Bar\n")
        overheard = roast_extraction.get('overheard_dialogue', [])
        if isinstance(overheard, list):
            for snippet in overheard:
                f.write(f"- *\"{snippet}\"*\n")
        else:
            f.write(f"- *\"{overheard}\"*\n")
    
    if roast_level.lower() != "off":
        print(f"Roast Recap exported to {roast_path}")

if __name__ == "__main__":
    SCENARIOS = load_scenarios()
    
    scenario_list = ", ".join(SCENARIOS.keys())
    parser = argparse.ArgumentParser(
        description="Run a TinyTruce conflict simulation.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("--scenario", type=str, default="domestic", 
                        help=f"The conflict scenario to run.\nAvailable scenarios: {scenario_list}")
    parser.add_argument("--turns", type=int, default=15, help="Number of turns to run the simulation.")
    
    agent_group = parser.add_argument_group('Agent Configuration')
    agent_group.add_argument("--agents", type=str, nargs="+", default=None, help="List of base agent files (e.g., vladimir_putin.agent.json)")
    agent_group.add_argument("--fragments", type=str, nargs="+", default=None, help="List of behavior fragment files")
    
    output_group = parser.add_argument_group('Output & UX Options')
    output_group.add_argument("--narrator", type=str, choices=["off", "salty", "neutral"], default="off", help="Enable the dry British Narrator voice.")
    output_group.add_argument("--roast-level", type=str, choices=["off", "mild", "spicy", "nuclear"], default="spicy", help="Set the intensity of the Roast Recap (or 'off' to disable).")
    output_group.add_argument("--hide-thoughts", action="store_true", help="UX Mode: Hide internal agent thinking blocks for a cinematic feed.")
    output_group.add_argument("--monologue", action="store_true", help="Address Mode: Single-agent sequential delivery with audience stimuli.")
    output_group.add_argument("--disable-injects", action="store_true", help="Disable the random mid-simulation dynamic injects/crisis events.")
    
    args = parser.parse_args()
    
    run_tinytruce_simulation(
        args.scenario, 
        args.turns, 
        args.agents, 
        args.fragments,
        args.narrator,
        args.roast_level,
        args.hide_thoughts,
        args.monologue,
        args.disable_injects
    )
