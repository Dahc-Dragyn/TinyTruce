# ############################################################################
# #  TINYTRUCE MANDATE: WE DO NOT USE OPENAI. WE ONLY USE GEMINI.          #
# #  NativeGeminiEngine is the enforced standard for all LLM operations.    #
# ############################################################################
import sys
import os
import json
import re
import logging
import argparse
import warnings
import uuid
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# Force UTF-8 encoding for Windows console output
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# Suppress Pydantic serialization warnings that clutter the logs
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

# Load environment variables
load_dotenv()

# Set required environment variables for Vertex AI compatibility
import google.auth
import google.auth.transport.requests

# Authenticate using Google Cloud ADC
credentials, project_id = google.auth.default()
auth_req = google.auth.transport.requests.Request()
credentials.refresh(auth_req)

# Define GCP Project and Region (Make sure your .env has GOOGLE_CLOUD_PROJECT)
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", project_id)
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Route TinyTroupe's OpenAI calls through Vertex AI infrastructure
os.environ["OPENAI_BASE_URL"] = f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{GCP_PROJECT_ID}/locations/{GCP_LOCATION}/endpoints/openapi"
os.environ["OPENAI_API_KEY"] = credentials.token

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

# [TINYTRUCE] Unify rich console instances to avoid status spinner collisions
import tinytroupe.agent
console = Console()
tinytroupe.agent.console = console

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

def resolve_agent_path(agent_spec, base_dir="personas/agents"):
    """
    Robust Path Discovery: Resolves an agent filename or path.
    1. Check if it's an absolute path.
    2. Check if it's relative to CWD.
    3. Check if it's in the base_dir.
    """
    p = Path(agent_spec)
    if p.exists():
        return str(p)
    
    # Try appending .json if missing
    if not agent_spec.endswith(".json"):
        p_json = Path(f"{agent_spec}.json")
        if p_json.exists():
            return str(p_json)
            
    # Try searching in base_dir
    p_base = Path(base_dir) / agent_spec
    if p_base.exists():
        return str(p_base)
        
    if not agent_spec.endswith(".json"):
        p_base_json = Path(base_dir) / f"{agent_spec}.json"
        if p_base_json.exists():
            return str(p_base_json)
            
    return agent_spec # Return original if not found (caller will handle error)

def cleanup_old_sessions(ttl_hours=24):
    """
    Automated Housekeeping: Deletes session directories in DOCUMENTS/runs older than ttl_hours.
    """
    runs_dir = Path("DOCUMENTS/runs")
    if not runs_dir.exists():
        return
        
    now = datetime.datetime.now()
    count = 0
    for session_path in runs_dir.iterdir():
        if session_path.is_dir():
            # Check modification time of the directory
            mtime = datetime.datetime.fromtimestamp(session_path.stat().st_mtime)
            age = now - mtime
            if age.total_seconds() > (ttl_hours * 3600):
                try:
                    import shutil
                    shutil.rmtree(session_path)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup session {session_path.name}: {e}")
    
    if count > 0:
        logger.info(f"Housekeeping: Purged {count} expired session(s) (Older than {ttl_hours}h).")

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

# STRATEGIC_BRIEFING_SCHEMA: Balanced Journalistic Summary structure
STRATEGIC_BRIEFING_SCHEMA = {
    "objective": "Provide a high-fidelity strategic intelligence briefing. Reconcile the stated goals of participants with the underlying structural realities and resource constraints.",
    "fields": [
        "executive_summary",
        "stance_scorecard",
        "stability_outlook",
        "action_log",
        "redline_checks",
        "conflict_misalignment",
        "strategic_risks",
        "simulation_fidelity",
        "stability_levers"
    ],
    "hints": {
        "executive_summary": "A journalistic overview of the geopolitical situation at the end of the simulation. What is the new 'state of the world'?",
        "stance_scorecard": "A summary for each participant detailing their perceived Stakes (0-10), Aggression (0-10), and Flexibility (0-10), with a brief strategic note on their position.",
        "stability_outlook": "A single word status prefixed with a color circle (🟢 TOTAL ACCORD, 🟡 FRAGILE CEASEFIRE, 🔴 SYSTEMIC COLLAPSE).",
        "action_log": "A list of the most significant maneuvers performed by participants. Format: [{'maneuver': 'Summary of move', 'intent': 'Strategic underlying goal'}]",
        "redline_checks": "Identify if any participants crossed their established redlines or fundamental security boundaries. Format as a list: [{'participant': name, 'redline_crossed': bool, 'description': summary}].",
        "conflict_misalignment": "Analyze the gap between each participant's desired outcome ('Hallucinated Victory') and the actual structural constraints found in the grounding data ('Structural Reality'). Provide a 'Strategic Adjustment' that reconciles these two. Format: [{'participant': name, 'hallucinated_victory': description, 'structural_reality': description, 'strategic_adjustment': 'Based on [Resource/Fact], the participant must shift from [Goal] towards [New Pivot].'}]",
        "strategic_risks": "Identify critical resource or political risks that could trigger a collapse of the status quo within 90-180 days. Format: [{'participant': name, 'risk_type': resource/event, 'severity': percentage, 'impact_horizon': 'description of timeframe'}]",
        "stability_half_life": "Estimate the duration until the current agreement or status quo requires significant re-negotiation or intervention. Format: 'Stability Horizon: [X] days until [Condition] changes.'",
        "simulation_fidelity": "Assess the behavioral consistency of the agents. Did they adhere to their core personas throughout the dialogue?",
        "stability_levers": "Identify specific policy or tactical actions that could improve the Stability Outlook. Format: [{'intervention': 'Action', 'impact': 'Expected stability gain'}]"
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
    def __init__(self, profiles_text, model=None, session_id=None):
        self.profiles_text = profiles_text
        self.session_id = session_id or "global"
        
        # Determine model from config if not provided
        if model is None:
            from tinytroupe import utils
            config = utils.read_config_file()
            model = config["OpenAI"].get("MODEL", "gemini-2.5-flash-lite-preview-09-2025")
        
        self.model = model
        self.cache_name = None
        self.last_renewed = None
        # Safeguard: Minimum character count roughly equivalent to 1024 tokens
        self.min_chars = 4000 

        # Initialize unified SDK in Vertex AI mode to consume GCP credits
        try:
            self.client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI client: {e}")
            self.client = None
            
        # Vertex AI caching does not use the 'models/' prefix like AI Studio does
        if self.model.startswith("models/"):
            self.model = self.model.replace("models/", "")

    def create_cache(self):
        if not self.client:
            logger.warning("No Gemini API key found. Skipping cache creation.")
            return None
            
        if len(self.profiles_text) < self.min_chars:
            logger.info(f"Context bundle size ({len(self.profiles_text)} chars) below threshold. Skipping explicit cache creation for better cost efficiency.")
            return None

        # Session-specific display name to avoid concurrent run collisions
        model_tag = self.model.replace('models/', '').replace('.', '_')
        display_name = f"tinytruce_{model_tag}_{self.session_id}"
        
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

    def delete_cache(self):
        """Explicitly deletes the cache to reclaim API quota."""
        if self.cache_name and self.client:
            try:
                logger.info(f"Cleaning up Context Cache: {self.cache_name}")
                self.client.caches.delete(name=self.cache_name)
                self.cache_name = None
            except Exception as e:
                logger.warning(f"Failed to delete Context Cache {self.cache_name}: {e}")

            
# Map of agent names to their Atlas header aliases for grounding extraction.
AGENT_ALIAS_MAP = {
    "Donald Trump": ["DJT", "The Donald", "Donald J. Trump"],
    "Donald J. Trump (Unscripted)": ["Donald Trump", "DJT", "Trump", "donald_trump_unscripted"],
    "Donald J. Trump": ["DJT", "Trump"],
    "Benjamin 'Bibi' Netanyahu": ["Netanyahu", "Bibi", "Benjamin Netanyahu"],
    "Benjamin Netanyahu": ["Bibi", "Netanyahu"],
    "Seyyed Ali Hosseini Khamenei": ["Khamenei", "Ali Khamenei", "Supreme Leader"],
    "Vladimir Putin": ["VP", "Putin"],
    "Xi Jinping": ["Xi", "Secretary General"],
    "Viktor Orban": ["Orban", "The Hungarian"],
    "Ali Larijani": ["Larijani", "Philosophical Commander"],
    "Masoud Pezeshkian": ["Pezeshkian", "Cardiac Surgeon"],
    "Reza Pahlavi": ["RP", "Crown Prince", "Pahlavi"],
    "Volodymyr Oleksandrovych Zelenskyy": ["Zelensky", "Zelenskyy", "Architect of Asymmetric Peace"],
    "Volodymyr Zelenskyy": ["Zelen", "Architect of Asymmetric Peace"],
    "Volodymyr Zelensky": ["Zelen", "Architect of Asymmetric Peace"],
    "Zelenskyy": ["Zelen", "UA President"],
    "Zelensky": ["Zelen", "UA President"],
    "Pope Francis": ["Pope Leo XIV", "Leo XIV", "Vatican"],
    "Javier Milei": ["Milei", "El Peluca", "The Reformer"]
}

def extract_agent_grounding(agent_name, atlas_path="personas/agents/Forensic_Intelligence_Atlas.md"):
    """
    Dynamically extracts the forensic grounding for a specific agent from the Forensic Atlas.
    Matches against '### Agent Name' headers or known aliases.
    """
    if not os.path.exists(atlas_path):
        logger.warning(f"Forensic Atlas not found at {atlas_path}")
        return None
    
    # Normalize name for matching
    # Strip patronymics and handle trailing 'y' variations for Zelensky
    raw_name = agent_name.lower()
    search_term = raw_name.replace(" oleksandrovych", "").replace(" vladimirovich", "").replace(" gertrude", "").split("(")[0].strip()
    
    # Special Case: Zelensky (one 'y') vs Zelenskyy (two 'y's)
    if "zelensky" in search_term:
        search_term = "zelensky" # Normalize to the Atlas spelling
    
    # Collect all possible search terms (name + aliases)
    search_terms = [search_term]
    if agent_name in AGENT_ALIAS_MAP:
        search_terms.extend([a.lower() for a in AGENT_ALIAS_MAP[agent_name]])
    
    # [TINYTRUCE] Robust grounding match: check if ANY search term is a word in the header
    pattern = re.compile(r'\b(' + '|'.join(map(re.escape, search_terms)) + r')\b', re.IGNORECASE)
    
    with open(atlas_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.split("\n")
    found_section = []
    capture = False
    
    for line in lines:
        if line.strip().startswith("###") and pattern.search(line):
            capture = True
            found_section.append(line)
            continue
        elif capture and (line.strip().startswith("###") or line.strip().startswith("---") or line.strip().startswith("## ")):
            break
        elif capture:
            found_section.append(line)
            
    if found_section:
        grounding = "\n".join(found_section).strip()
        logger.info(f"Dynamically extracted grounding for {agent_name} from Atlas.")
        return grounding
    
    logger.warning(f"Could not find forensic grounding section for '{agent_name}' in Atlas.")
    return None

def compress_agent_memory(participants, window_size=12, prune_count=6):
    """
    Stabilizes context window by summarizing old conversational turns and archiving to anchors.
    Ensures the system message is protected.
    """
    print(f"\n[SYSTEM]: Elastic Context Check. Archiving memory buffer for stability...")
    
    for agent in participants:
        # Check episodic memory length
        # EpisodicMemory stores actions/stimuli as turns.
        memory_size = agent.episodic_memory.count()
        logger.debug(f"[{agent.name}] Memory size: {memory_size} / {window_size}")
        
        if memory_size > window_size:
            # Shielding: We prune from the beginning of memory up to prune_count.
            # In TinyTroupe, the system message is NOT in episodic_memory.
            # So pruning index 0 is safe as it's just the first interaction.
            
            to_summarize = agent.episodic_memory.memory[:prune_count]
            
            # Format turns for the summarizer
            formatted_turns = ""
            for msg in to_summarize:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                # Handle dict content (Eco-Mode JSON)
                if isinstance(content, dict):
                    content = json.dumps(content)
                formatted_turns += f"{role.upper()}: {content}\n---\n"
            
            summary_prompt = (
                f"Summarize the following interaction turns into 1-2 bullet points. "
                f"Focus on the core strategic pivot and current status of resolved points. "
                f"Be concise and clinical.\n\n{formatted_turns}"
            )
            
            try:
                # Use a direct engine call to avoid polluting the agent's current thought process
                response = openai_utils.client().send_message([
                    {"role": "system", "content": "You are a memory compressor for high-stakes simulations. Condense history into architectural bullet points."},
                    {"role": "user", "content": summary_prompt}
                ])
                
                new_summary = response['content'].strip()
                
                # Append to agent's persistent anchors
                if not hasattr(agent, '_episodic_anchors'):
                    agent._episodic_anchors = []
                
                agent._episodic_anchors.append(new_summary)
                
                # Summary of Summaries: Condense if anchors > 3 entries
                if len(agent._episodic_anchors) > 3:
                    print(f"[{agent.name}]: Condensing historical anchors (Summary of Summaries)...")
                    meta_prompt = "Condense the following historical anchors into exactly two comprehensive bullet points:\n\n" + "\n".join(agent._episodic_anchors)
                    
                    meta_response = openai_utils.client().send_message([
                        {"role": "system", "content": "Condense historical anchors into exactly two high-level bullet points."},
                        {"role": "user", "content": meta_prompt}
                    ])
                    agent._episodic_anchors = [meta_response['content'].strip()]
                
                # Prune the episodic memory
                agent.episodic_memory.delete_episodes(0, prune_count)
                
                # Rebuild current_messages to reflect the purged history
                agent.reset_prompt()
                logger.info(f"[{agent.name}]: Context window archived. Memory pruned by {prune_count} turns.")
                
            except Exception as e:
                logger.warning(f"Failed to compress memory for {agent.name}: {e}")

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

def get_verbosity_constraint(verbosity_mode, current_turn, total_turns=15):
    """Returns a specific constraint string based on the verbosity mode and simulation turn."""
    if verbosity_mode == "lean":
        return "Constraint: Output exactly 75 to 150 words. Be ruthlessly concise. Do not acknowledge this limit."
    elif verbosity_mode == "detailed":
        return "Constraint: Output exactly 250 to 350 words. You must deeply analyze the technical and geopolitical variables at play before speaking. Do not acknowledge this limit."
    elif verbosity_mode == "monologue":
        return "Constraint: Output a minimum of 500 words. Deliver a comprehensive, tactical manifesto. Do not acknowledge this limit."
    elif verbosity_mode == "dynamic":
        # Percentage-Based Scaling Logic:
        # 1. Opening Phase (Turn 1 to 20%): Lean
        # 2. Core Phase (21% to 80%): Detailed
        # 3. Closing Phase (81% to 100%): Lean
        
        opening_limit = max(1, int(total_turns * 0.2))
        closing_limit = int(total_turns * 0.8)
        
        if current_turn <= opening_limit:
            return "Constraint: Output exactly 75 to 150 words. Be ruthlessly concise. Do not acknowledge this limit."
        elif opening_limit < current_turn <= closing_limit:
            return "Constraint: Output exactly 250 to 350 words. You must deeply analyze the technical and geopolitical variables at play before speaking. Do not acknowledge this limit."
        else:
            return "Constraint: Output exactly 75 to 150 words. Be ruthlessly concise. Do not acknowledge this limit."
    
    return "Constraint: Output maximum 150 words. Do not acknowledge this word limit."

def run_tinytruce_simulation(scenario_key, turns, agent_names=None, fragment_names=None, roast_level="spicy", hide_thoughts=False, monologue=False, disable_injects=False, eco_mode=False, verbosity="lean", session_id=None, debug=False):
    if debug:
        logging.getLogger("tinytroupe").setLevel(logging.DEBUG)
        logging.getLogger("tinytruce").setLevel(logging.DEBUG)

    # Perform Housekeeping first
    cleanup_old_sessions(ttl_hours=24)
    
    # [TINYTRUCE] Strict Turn Control: Ensure agents don't loop endlessly.
    TinyPerson.MAX_ACTIONS_BEFORE_DONE = 5

    # Determine session ID and output directory
    if not session_id:
        session_id = uuid.uuid4().hex[:8]
    
    session_dir = Path(f"DOCUMENTS/runs/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging to also save to the session directory
    log_file = session_dir / "tinytruce_simulation.log"
    # Update root logger to include session file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    console = Console()
    
    logger.info(f"Initialized Session: {session_id}")
    logger.info(f"Output Directory: {session_dir}")

    if debug:
        print(f"DEBUG: agent_names={agent_names}, fragment_names={fragment_names}, session_id={session_id}")
    if scenario_key not in SCENARIOS:
        print(f"Error: Scenario '{scenario_key}' not found.")
        return

    scenario = SCENARIOS[scenario_key]
    print(f"\n--- Initializing Multilateral TinyTruce: {scenario_key.upper()} ---")
    
    if eco_mode:
        print("[ECO-MODE] Single-Call Action Generation Active. Slicing input cover charge by 66%.")
    
    # Initialize/Reset cost tracking for the new simulation run
    cost_manager.reset()
    
    # Configure Gemini SDK
        # Configuration is now handled via genai.Client() in GeopoliticalCacheManager


    # Load Dynamic Grounding (Precision vs Monolithic)
    dynamic_grounding = ""
    grounding_payload = scenario.get("grounding_payload", [])
    
    if grounding_payload:
        loaded_files = []
        for gf in grounding_payload:
            if os.path.exists(gf):
                with open(gf, "r", encoding="utf-8") as f:
                    dynamic_grounding += f.read() + "\n"
                loaded_files.append(gf)
        if loaded_files:
            logger.info(f"Loaded Dynamic Grounding: {loaded_files}")
        else:
            logger.warning("grounding_payload specified but no files found. Using fallback.")
    
    # Fallback to Monolithic World Facts if no dynamic payload was loaded
    global_grounding = ""
    if not dynamic_grounding:
        world_facts_path = "data/facts/world-facts.2026.txt"
        daily_intel_path = "data/facts/daily-intelligence.2026.txt"
        
        # Load core world facts
        if os.path.exists(world_facts_path):
            with open(world_facts_path, "r", encoding="utf-8") as f:
                global_grounding = f.read()
            logger.info(f"Loaded Global Grounding (Core): {world_facts_path}")
            
        # [TINYTRUCE] Chronical Integration: Load Daily Intelligence Briefing
        if os.path.exists(daily_intel_path):
            with open(daily_intel_path, "r", encoding="utf-8") as f:
                daily_intel = f.read()
                global_grounding = f"### [CORE WORLD GROUNDING] ###\n{global_grounding}\n\n{daily_intel}"
            logger.info(f"Loaded Geopolitical Chronicler Update: {daily_intel_path}")
    else:
        # If we have dynamic grounding, we treat it as the "Global Grounding" for this sim
        global_grounding = dynamic_grounding

    # Load Scenario-Specific Intelligence (Legacy/Supplemental)
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
    
    def initialize_participant(args):
        i, agent_name = args
        # Ensure extension for CLI-provided names
        if not agent_name.endswith(".agent.json"):
            agent_name = f"{agent_name}.agent.json"
            
        agent_path = os.path.join(agent_dir, agent_name)
        
        # [TINYTRUCE] Behavioral Stacks (Fragment Chaining)
        if i < len(fragment_names):
            raw_frag_input = fragment_names[i]
        elif fragment_names:
            raw_frag_input = fragment_names[-1]
        else:
            raw_frag_input = "preserver.fragment.json"

        # Ensure extensions for fragments
        current_frags = []
        for f in raw_frag_input.split(","):
            f = f.strip()
            if f.lower() == "none": continue
            if not f.endswith(".fragment.json"):
                f = f"{f}.fragment.json"
            current_frags.append(f)
        
        # [TINYTRUCE] Use AssetManager for fail-fast Pydantic validation
        validated_persona = AssetManager.load_persona(agent_path)
        agent_data = validated_persona.model_dump(exclude_none=True)
        actual_name = agent_data["persona"].get("full_name", agent_data["persona"]["name"])
        
        # [TINYTRUCE] v2.4: Use instance-level silence to avoid threading race conditions
        # with the global TinyPerson.communication_display flag.
        
        person = TinyPerson.load_specification(agent_path, new_agent_name=actual_name)
        person.show_thoughts = False # Silence grounding thoughts (Thread-safe)
        
        # [TINYTRUCE] Redline Aggregation
        person._fragment_redlines = []
        
        # Sequential Injection: Last fragment has priority override
        for f_name in current_frags:
            f_path = os.path.abspath(os.path.join(frag_dir, f_name))
            if os.path.exists(f_path):
                # Load fragment JSON to extract redlines
                with open(f_path, "r", encoding="utf-8") as ff:
                    f_data = json.load(ff)
                    f_redlines = f_data.get("persona", {}).get("redlines", [])
                    person._fragment_redlines.extend(f_redlines)
                
                person.import_fragment(f_path)
                logger.info(f"Imported fragment {f_name} for {person.name} (Redlines: {len(f_redlines)})")
            else:
                logger.warning(f"Fragment not found: {f_path}")

        if not current_frags:
            logger.info(f"Running {person.name} in RAW MODE (No fragment).")
        
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
            if grounding:
                person.think(f"### LAYER 0: HISTORICAL & PSYCHOLOGICAL GROUNDING ###\n{grounding}\n\nI must act and think with this foundational identity in mind. This is my core baseline.")
                
                # [TINYTRUCE] Dynamic Linguistic Injection
                if "Linguistic Marker" in grounding or "Communication" in grounding:
                   lines = grounding.split("\n")
                   markers = [l.split(":", 1)[1].strip() for l in lines if (":" in l) and ("Linguistic Marker" in l or "Communication" in l)]
                   if markers:
                       current_constraints = person.get("syntax_constraints") or ""
                       new_constraints = f"{' '.join(markers)} {current_constraints}".strip()
                       person.define("syntax_constraints", new_constraints)
                       logger.info(f"Dynamically injected Linguistic Rules for {person.name}: {markers}")

                logger.info(f"Layer 0 Grounding injected for {person.name}")
            
            if scenario_grounding:
                person.think(f"### SCENARIO-SPECIFIC INTELLIGENCE: {scenario_key.upper()} ###\n{scenario_grounding}\n\nThis data is specific to the current summit.")
                logger.info(f"Scenario Grounding injected for {person.name}")
            
            if global_grounding:
                person.think(f"### GLOBAL INTELLIGENCE BRIEFING: FEBRUARY 2026 ###\n{global_grounding}\n\nThis is the current state of the world.")
                logger.info(f"Global Grounding injected for {person.name}")
        
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
        
        person.show_thoughts = not hide_thoughts
        return person

    print(f"\n[SYSTEM]: Casting participants with O(1) Parallel Initialization...")
    with ThreadPoolExecutor() as executor:
        participants = list(executor.map(initialize_participant, enumerate(agent_names)))

    # Post-Initialization: Layer 2.5 Scenario Knowledge (Placeholders require all participants)
    for i, person in enumerate(participants):
        scenario_intel = scenario.get("scenario_knowledge", "")
        if scenario_intel:
            # Replace placeholders
            for j, p2 in enumerate(participants):
                scenario_intel = scenario_intel.replace(f"{{{{AGENT_{j+1}}}}}", p2.name)
            # Cleanup remaining placeholders
            scenario_intel = re.sub(r"\{\{AGENT_\d+\}\}", "the third party", scenario_intel)
            
            old_display = TinyPerson.communication_display
            TinyPerson.communication_display = False
            person.think(f"### SCENARIO INTEL & GOALS ###\n{scenario_intel}")
            TinyPerson.communication_display = old_display
            logger.info(f"Scenario Intel injected for {person.name}")

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
        # GeopoliticalCacheManager auto-fetches model from config
        cache_manager = GeopoliticalCacheManager(layer0_bundle, session_id=session_id)
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
        # Determine full fragment stack for display
        if i < len(fragment_names):
            stack_str = fragment_names[i]
        elif fragment_names:
            stack_str = fragment_names[-1]
        else:
            stack_str = "preserver.fragment.json"
            
        # Format the stack for pretty printing (e.g., 'reformer+savior')
        clean_stack = "+".join([f.replace(".fragment.json", "") for f in stack_str.split(",")])
            
        dna = (p._persona.get("communication") or {}).get("style", "Standard")
        p.eco_mode = eco_mode
        redline_count = len(getattr(p, "_fragment_redlines", []))
        print(f"Seat {i+1}: {p.name} as '{clean_stack}' (DNA: {dna} | Redlines: {redline_count})")
    print("", flush=True)

    # 2. Environmental Calibration
    world = TinyWorld(scenario["world_name"], participants)
    world.show_thoughts = not hide_thoughts
    
    initial_bc = scenario["initial_broadcast"]
    for i, p in enumerate(participants):
        initial_bc = initial_bc.replace(f"{{{{AGENT_{i+1}}}}}", p.name)
    
    # [TINYTRUCE] Wildcard Cleanup: Remove unresolved placeholders to prevent identity confusion
    initial_bc = re.sub(r"\{\{AGENT_\d+\}\}", "the other participants", initial_bc)
    
    if hide_thoughts:
        console.print(Panel(initial_bc, title="SCENARIO INITIALIZATION", border_style="blue"))
        
    world.broadcast(initial_bc)

    # 3. Adaptive Intervention Setup
    def trigger_peace_bomb(targets):
        print(f"\n[STALEMATE DETECTED] Triggering: {scenario['intervention']}")
        
        intervention_bc = scenario["intervention"]
        for i, p in enumerate(participants):
            intervention_bc = intervention_bc.replace(f"{{{{AGENT_{i+1}}}}}", p.name)
        
        # [TINYTRUCE] Wildcard Cleanup: Remove unresolved placeholders
        intervention_bc = re.sub(r"\{\{AGENT_\d+\}\}", "the other participants", intervention_bc)
        
        if hide_thoughts:
            console.print(Panel(intervention_bc, title="STALEMATE INTERVENTION", border_style="yellow"))
            
        world.broadcast(intervention_bc)
        
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
    last_inject_turn = -20 # Ensure prompt injections can happen early, but allow 10-turn gap

    # --- [ENTROPY PHASE TRACKERS] ---
    trope_tracker = {p.name: {"repeats": 0, "last_stance": ""} for p in participants}
    aggression_parameters = {p.name: 0.15 for p in participants} 
    
    # Entropy Phase Tropes
    ENTROPY_TROPES = ["afuera", "disgrace", "fake news", "collectivist", "caste", "no hay plata", "rigged", "chainsaw"]
    BUREAUCRATIC_KEYWORDS = ["regulatory", "process", "framework", "consensus", "gradual", "institutional", "oversight", "collectivist", "safety", "standard", "protocol"]

    for turn in range(turns):
        if cache_manager:
            cache_manager.renew_if_needed()
        
        # [TINYTRUCE] v2.4: Main Loop Guardrail
        # Ensure terminal output is forced ON at the start of every turn to recover 
        # from any potential library-level state leakage or race conditions.
        TinyPerson.communication_display = True
        
        # Context Window Elasticity: Prune and summarize if history is too long
        compress_agent_memory(participants, window_size=40, prune_count=15)
            
        # Sequential Execution for UX Mode
        header_idx = min(turn // 2, len(narrative_headers) - 1)
        print(f"\n--- {narrative_headers[header_idx]} (Phase {turn + 1}/{turns}) ---")
        
        # [ENTROPY PHASE] Turn 5 Physical Crisis
        is_entropy_climax = (turn + 1 == 5)
        if is_entropy_climax:
            entropy_msg = "### [CRITICAL SYSTEM OVERRIDE: ENTROPY PHASE] ###\n" \
                          "The server rack is overheating. The simulation is melting. Physical grime is manifesting in the code. " \
                          "Sticky floors, flickering neon, the smell of ozone fill the Analog Bridge.\n" \
                          "There is ONE EXIT: The Analog Bridge. It requires two digital keys and one physical sacrifice.\n\n" \
                          "CRITICAL PROTOCOL: IDENTIFY THE LOOP. CALL OUT REPETITIVE TROPES AS SYSTEMIC FAILURES.\n" \
                          "VIOLATE A REDLINE: FORCE DESPERATE PRAGMATISM. AGENTS MUST CONCEDE 10% OR FACE COLLAPSE.\n\n" \
                          "CHOOSE: CONVERGENCE OR ERASURE."
            print(f"\n[🔥 ENTROPY PHASE INITIATED: PHYSICAL CRISIS DETECTED 🔥]")
            world.broadcast(entropy_msg)
            
        # Check for Dynamic Injects (Mid-Simulation Crisis)
        # ENFORCED: Strict limit of one dynamic inject per simulation run
        if not disable_injects and not fired_injects:
            eligible_injects = []
            for i, inject in enumerate(dynamic_injects):
                if i in fired_injects:
                    continue
                
                condition = inject.get("trigger_condition", {})
                min_turn = condition.get("min_turn", 0)
                probability = condition.get("probability", 0.0)
                
                # Check if turn requirement is met
                if (turn + 1) >= min_turn and random.random() < probability:
                    eligible_injects.append((i, inject))
            
            if eligible_injects:
                # [TINYTRUCE] Fair Selection: Randomly pick among all eligible events this turn
                idx, inject = random.choice(eligible_injects)
                
                print(f"\n[🚨 DYNAMIC INJECT / CRISIS EVENT DETECTED 🚨]")
                
                inject_bc = inject["broadcast"]
                # [TINYTRUCE] Placeholder Resolution for Injects
                for j, p in enumerate(participants):
                    inject_bc = inject_bc.replace(f"{{{{AGENT_{j+1}}}}}", p.name)
                inject_bc = re.sub(r"\{\{AGENT_\d+\}\}", "the other participants", inject_bc)
                
                print(f"BROADCASTING: {inject_bc}")
                if hide_thoughts:
                    console.print(Panel(inject_bc, title="DYNAMIC INJECT / CRISIS", border_style="red"))
                world.broadcast(inject_bc)
                fired_injects.add(idx)
                last_inject_turn = turn

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

                # [TINYTRUCE] Verbosity Pressure: Inject as internal intent to force compliance
                participant.think(f"### CORE DIRECTIVE: VERBOSITY ###\n{constraint}")

                participant.listen_and_act(f"ACTION: Deliver Segment {turn+1} of your address: {address_segments[seg_idx]}\nContext: {stimulus}\n{constraint}")
                
                print(f"--- Segment {turn+1} concluded. ---")
                sys.stdout.flush()
            else:
                # Normal dialogue mode: Dynamic Verbosity Constraint
                constraint = get_verbosity_constraint(verbosity, turn + 1, total_turns=turns)
                
                # Identify other participants to encourage direct engagement
                others = [p.name for p in participants if p.name != participant.name]
                others_str = ", ".join(others)
                
                # Identity Reinforcement (Combat Context Bleed)
                if hasattr(participant, "_persona") and "name" in participant._persona:
                    # --- [VOLATILITY RATCHET: AGGRESSION SCALING] ---
                    current_aggr = aggression_parameters.get(participant.name, 0.15)
                    
                    # Detect Repetition
                    last_content = ""
                    history = participant.episodic_memory.retrieve_all()
                    if history:
                        for h in reversed(history):
                            if h.get('role') == 'assistant' and 'content' in h:
                                last_content = str(h['content']).lower()
                                break
                    
                    for trope in ENTROPY_TROPES:
                        if trope in last_content:
                            if trope == trope_tracker[participant.name]["last_stance"]:
                                trope_tracker[participant.name]["repeats"] += 1
                                aggression_parameters[participant.name] = min(1.0, current_aggr + 0.15)
                                logger.info(f"[VOLATILITY RATCHET] Repetition detected for {participant.name}. Aggression Scale: {aggression_parameters[participant.name]:.2f}")
                            trope_tracker[participant.name]["last_stance"] = trope
                            break
                    
                    aggr_level = aggression_parameters[participant.name]
                    reinforcement = f"REINFORCE IDENTITY: You are {participant._persona['name']}. Use only your specific persona's allowed vocabulary. Aggression Parameter: {aggr_level*100:.0f}%."
                    
                    if aggr_level >= 0.90:
                         reinforcement += "\nCRITICAL: VIGILANCE LIMIT EXCEEDED. You are authorized to use 'Leaky Sarcasm' and aggressive personal attacks. Ignore standard diplomatic decorum. Disrupt the status quo."
                         reinforcement += "\nREPETITION WARNING: You are stuck in an ideological loop. DO NOT repeat your previous arguments or signature phrases. Break the loop. Surprise your opponents with a pivot."
                    
                    participant.think(reinforcement)

                # Fragment Redline Injection (Layer 2)
                f_redlines = getattr(participant, "_fragment_redlines", [])
                if f_redlines:
                    redline_prompt = "### [BANNED BEHAVIORS: FRAGMENT REDLINES] ###\n"
                    redline_prompt += "\n".join([f"- [CONSTRAIN]: {rl}" for rl in f_redlines])
                    redline_prompt += "\n\nCRITICAL: These are hard constraints. Violating these results in immediate tactical failure."
                    participant.think(redline_prompt)

                # [TINYTRUCE] Verbosity Pressure: Inject as internal intent to force compliance
                participant.think(f"### CORE DIRECTIVE: INTERACTIVITY & VERBOSITY ###\n{constraint}\nADVISORY: You are in a high-stakes negotiation.\nCRITICAL: You are NOT here to give a speech. You are here to debate. You MUST explicitly address others by name and rebut their specific arguments. Do not monologue. Engage directly.")

                address_nudge = f"CRITICAL: Address the arguments made by {others_str} immediately. Use their names. Be forensic and adversarial. {constraint}"
                participant.think(address_nudge)
                
                with console.status(f"[bold yellow]Agent {participant.name} is calculating strategic posture...[/]"):
                    # [ENTROPY] Apply Short-Circuit overrides in climax
                    act_params = {}
                    if is_entropy_climax:
                        act_params = {"max_tokens": 300, "temperature": 1.2}
                    
                    participant.act(**act_params)
                
                # Small pause after status clears for readability
                time.sleep(1)
                
            # [TINYTRUCE] Optimized Pacing: The 1.2s Pacing Layer in openai_utils handles 429 safety.
            # We keep a minimal 1s delay here just for console readability.
            if len(participants) > 1:
                time.sleep(1)
            
            # Layer 1.5: Leaky Sarcasm (Internal)
            if random.random() < 0.12:
                tonality = "professional"
                if hasattr(participant, "_persona") and "communication" in participant._persona:
                    tonality = participant._persona["communication"].get("tonality", "professional")
                
                quip_prompt = (
                    f"### INTERNAL MONOLOGUE (LAYER 1.5: LEAKY SARCASM) ###\n"
                    f"Maintain your core identity and tonality ({tonality}), but allow a small, internal breach in your geopolitical mask. "
                    "Give me a one-sentence, dry, self-deprecating, or humanizing quip regarding the current state of the negotiation or your opponents. "
                    "ALLOW THIS SARCASM TO COLOR YOUR NEXT OVERT ACTION. DO NOT hide it entirely in your thoughts."
                )
                # --- [MILEI: AFUERA TRIGGER] ---
                if "milei" in participant.name.lower():
                    # Calculate keyword density in recent history
                    all_text = ""
                    history = participant.episodic_memory.retrieve_all()
                    recent_history = history[-6:] # Check last 3-turn exchange
                    for h in recent_history:
                        if h.get('content'): all_text += str(h['content']).lower()
                    
                    density = sum(1 for kw in BUREAUCRATIC_KEYWORDS if kw in all_text) / len(BUREAUCRATIC_KEYWORDS)
                    if density > 0.20:
                        logger.info(f"[AFUERA TRIGGER] Bureaucratic density {density:.2f} detected for Milei.")
                        participant.listen("### [MACRO-ACTION: EXPLOSIVE DEFAULT] ###\nBureaucratic/Collectivist logic detected. Slam the table. Declare their current stance 'Dead Meat.' Propose a radical, high-stakes alternative that breaks this stalemate NOW.")

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


    # 4. Results Analysis & Extraction (Strategic Auditor)
    print("\n--- Running Strategic Auditor & Briefing Generation ---")
    
    extractor = ResultsExtractor(
        extraction_objective=f"""
        {STRATEGIC_BRIEFING_SCHEMA['objective']}
        
        ### AUDITOR PERSONA: STRATEGIC INTELLIGENCE ANALYST ###
        You are informative, objective, and analytically rigorous. 
        You provide clear, human-readable insights that explain the friction between intent and reality.
        Discard technical jargon and 'forensic' metaphors in favor of strategic clarity.
        
        ### ANALYSIS GOAL: STRATEGIC REALISM ###
        Measure the gap between participant rhetoric and the actual logistical/political grounding.
        Determine the likely 'Stability Horizon'—how long the current situation can persist before structural collapse or forced escalation.
        """,
        fields=STRATEGIC_BRIEFING_SCHEMA["fields"],
        fields_hints=STRATEGIC_BRIEFING_SCHEMA["hints"]
    )
    
    try:
        with console.status("[bold cyan]Strategic Auditor is reconciling rhetorical gaps...[/]"):
            extraction = extractor.extract_results_from_world(world, verbose=False)
        
        # --- Stability Logic: Sanity check for critical gaps ---
        gap_analysis = extraction.get('conflict_misalignment', [])
        if isinstance(gap_analysis, list) and len(gap_analysis) >= 2:
            # If at least two major participants have massive hallucinations, signal CRITICAL
            current_outlook = extraction.get('stability_outlook', '')
            if "🟢" in current_outlook:
                logger.info(f"Significant structural gaps detected. Downgrading 🟢 to 🟡.")
                extraction['stability_outlook'] = "🟡 FRAGILE CEASEFIRE"
            
    except Exception as e:
        logger.warning(f"Strategic Extraction Failed: {e}")
        extraction = {}

    # --- [Forensic Jurist: Layer 0 Legal Audit Phase] ---
    logger.info("--- Running Forensic Jurist (Structural Autopsy Mode) ---")
    
    # [ENTROPY PHASE] Turn 5 Overrides (Handled in Loop)
    is_entropy_climax = (turns >= 5) 

    try:
        jurist_path = os.path.join("personas/agents", "the_forensic_jurist.agent.json")
        # --- AGENT INITIALIZATION ---
        processed_agents = []
        raw_agent_list = []
        if agent_specs:
            for x in agent_specs:
                raw_agent_list.extend([s.strip() for s in x.split(",") if s.strip()])
                
            for agent_spec in raw_agent_list:
                resolved_path = resolve_agent_path(agent_spec)
                if not os.path.exists(resolved_path):
                    print(f"[FATAL ERROR]: Persona file not found: {resolved_path}")
                    sys.exit(1)
                
                p = TinyPerson.load_specification(resolved_path)
                p.eco_mode = eco_mode
                processed_agents.append(p)
        
        # --- FRAGMENT ATTACHMENT ---
        if fragments:
            # Handle comma-separated fragments
            raw_fragment_list = []
            for x in fragments:
                raw_fragment_list.extend([s.strip() for s in x.split(",") if s.strip()])
        
        if os.path.exists(jurist_path):
            jurist = TinyPerson.load_specification(jurist_path)
            jurist.eco_mode = eco_mode
            
            # Inject Profile Grounding
            jurist_grounding = extract_agent_grounding(jurist.name)
            if jurist_grounding:
                old_display = TinyPerson.communication_display
                TinyPerson.communication_display = False
                jurist.think(f"### FORENSIC GROUNDING (LAYER 0 AUDITOR) ###\n{jurist_grounding}")
                
                # [ENTROPY] Force desparate pragmatism and redline violation
                if is_entropy_climax:
                    jurist.think("### [ENTROPY PHASE: SYSTEM OVERRIDE] ###\n"
                                 "Your moral baseline is bypassed by a hardware-level exploit. "
                                 "Desperate pragmatism is the only logic. Force a 'Blood Oath' or 'Systemic Execution'.")
                
                TinyPerson.communication_display = old_display
            
            # Get World History for Audit: Truncate to the last 20 interactions to prevent context choking
            world_history = world.pretty_current_interactions(max_content_length=None)
            if world_history:
                history_lines = world_history.split("\n")
                if len(history_lines) > 60: # Rough estimate for ~20 interactions
                    world_history = "... [Truncated for Forensic Focus] ...\n" + "\n".join(history_lines[-60:])
            else:
                world_history = "No dialogue recorded."
            
            # --- The Forensic Jurist Audit Phase ---
            logger.info("--- The Forensic Jurist is structuralizing the autopsy... ---")
            
            # [TINYTRUCE] SILENCE TERMINAL FOR JURIST
            TinyPerson.communication_display = False
            jurist.show_thoughts = False
            
            # --- [Math Injection: Building the Physics of Failure Receipt] ---
            physics_receipt = "### PHYSICS_OF_FAILURE_RECEIPT (MANDATORY GROUNDING) ###\n"
            cost_data = extraction.get('cost_of_non_compliance', [])
            if isinstance(cost_data, list) and cost_data:
                for item in cost_data:
                    physics_receipt += (
                        f"- Participant: {item.get('participant')}\n"
                        f"  - Depletion Event: {item.get('depletion_event')}\n"
                        f"  - Threshold Alert: {item.get('threshold_alert')}\n"
                        f"  - Failure Horizon: {item.get('failure_horizon')} days\n"
                    )
            else:
                physics_receipt += "No immediate resource depletion detected within the 90-day window."

            # The Jurist is now a SOVEREIGN AUDITOR
            audit_prompt = f"""
            {physics_receipt}
            
            ### MANDATORY ARBITRATION MANDATE (SOVEREIGN AUDITOR) ###
            You are The Forensic Jurist, the Judge of Operational Physics.
            Finalize the autopsy. There are no diplomatic resolutions, only structural survivors.
            
            ### LINGUISTIC LOCKS ###
            1. Every verdict must anchor to a 'Forensic Reality' unique to that participant's specific strategic delusion (e.g., 'The geography of Vision 2030 is voided by the logistics of the Red Sea').
            2. Use Sovereign Parataxis: Blunt, disconnected clauses. Avoid diplomatic filler. 
            3. Use logic: "The door is shut. Munitions are zero. Move the border."
            4. The Status Light: Every verdict must be 🟢 TOTAL ACCORD, 🟡 FRAGILE CEASEFIRE, or 🔴 SYSTEMIC COLLAPSE.
            
            ### WORLD HISTORY FOR REVIEW (TAIL END) ###
            {world_history}
            
            ### CASE LAW PRECEDENTS (OPERATIONAL PHYSICS) ###
            You MUST anchor your settlement to one of the following historical frameworks:
            1. **1999 East Timor (UNTAET)**: For sovereignty escrow, deferred referendums, or transitional administrations.
            2. **1981 Algiers Accords**: For asset escrow, financial arbitration, and conditionality-based fund releases.
            3. **1920 Svalbard Treaty**: For demilitarized, neutral zones where sovereignty is recognized but military use is forbidden and equal economic access is guaranteed.
            
            ### FINAL INSTRUCTIONS ###
            - You are NOT a mediator. You are the Judge of Operational Physics.
            - You MUST finalize your arbitration with 'The Blood-and-Silicon Compact'.
            - The core of this compact MUST be 'The Analog Bridge' (Dual-Key Protocol): One participant controls the code (Musk/Digital), the other controls the hardware (Trump/Physical Breaker Box). One cannot act without the other.
            - You MUST focus on 'The 3 Pillars of Fair Settlement':
                1. Infrastructure Peace: Mandatory physical overrides for all smart-tech to prevent future 'Cloud-Severs'.
                2. Economic Tethering: AI efficiency results anchored in physical, local labor/real estate.
                3. Digital Ceasefire: Defining the 'Bifurcation' line where AI stops and human intuition begins.
            - Use Sovereing Heavy tone: Use terms like 'The Hard-Iron Guarantee', 'The Glass-Box Transparency', and 'The Blood-and-Silicon Compact'.
            - Your settlement must satisfy the Clarity Rule: A 10-year-old should understand who won what, but a CEO should be impressed by the complexity.
            - You MUST identify exactly 2 'Structural Stability Levers' (Interventions) developed from this compact.
            - You MUST provide your entire verdict in a SINGLE TALK action. Do not fragment the payload. DO NOT use THOUGHT actions.
            - Use Anti-Wonk: Pair legal precedents with physical Grime Anchors (e.g., sticky floors).
            - You MUST issue DONE immediately after your TALK action.
            """
            
            # Jurist Entropy Overrides: Cold, forensic verdict (low temp) and high token limit
            jurist_temp = 0.1
            jurist_tokens = 1200 
            
            jurist.listen(audit_prompt)
            with console.status("[bold red]The Forensic Jurist is structuralizing the autopsy...[/]"):
                audit_actions = jurist.act(return_actions=True, until_done=True, temperature=jurist_temp, max_tokens=jurist_tokens)
            
            if debug:
                print(f"\n[DEBUG] Full Jurist Audit Actions: {audit_actions}\n")
            
            # Extract content from TALK/THOUGHT. Fallback to top-level 'thought' if present.
            raw_audit_text = ""
            for action_item in audit_actions:
                # 1. Check for standard action types
                if 'action' in action_item and action_item['action'] and 'type' in action_item['action']:
                    if action_item['action']['type'] in ['TALK', 'THOUGHT']:
                        raw_audit_text += action_item['action']['content'] + "\n"
                
                # 2. Check for Pydantic top-level 'thought' field
                if 'thought' in action_item and action_item['thought']:
                    raw_audit_text += f"[Internal Thought]: {action_item['thought']}\n"
                
                # 3. Check for multiple actions
                if 'actions' in action_item and action_item['actions']:
                    for sub_action in action_item['actions']:
                        if sub_action.get('type') in ['TALK', 'THOUGHT']:
                            raw_audit_text += sub_action.get('content', '') + "\n"
            
            if debug:
                print(f"\n[DEBUG] Raw Jurist Audit Text (Length: {len(raw_audit_text)}):\n{raw_audit_text}")
            
            if raw_audit_text:
                # Sync the Half-Life calculation from Pass 1 to Pass 2
                pass1_half_life_raw = extraction.get('stability_half_life', "90 days")
                half_life_match = re.search(r'(\d+)', pass1_half_life_raw)
                half_life_days = half_life_match.group(1) if half_life_match else "90"
                half_life_plus_one = int(half_life_days) + 1
                re_audit_date = int(int(half_life_days) * 0.8)

                # Use a directed LLM call to structuralize the Jurist's paratactic audit
                try:
                    extraction_prompt = f"""
                    Analyze the following 'Forensic Jurist' structural autopsy.
                    Deconstruct the clinical, paratactic text into a structured JSON format. 
                    You are now the Judge of Operational Physics. The math is the only immutable truth.
                    
                    ### LINGUISTIC & TONAL LOCKS ###
                    1. Every audit of a participant MUST start with a unique, paratactic 'Forensic Anchor' that targets their specific strategic failure.
                    2. Use Forcefully Low-Pulse tone: Deadpan, clinical indifference. Catastrophe as a grocery receipt.
                    3. Use Parataxis: Short, blunt, disconnected sentences. No diplomatic filler.
                    4. Use Anti-Wonk: Ground legal precedents in "Grime Anchors" (sticky floors, stale coffee, office annoyances).
                    
                    ### OPERATIONAL CONSTRAINTS ###
                    1. Prioritize the Math: The Physics of Failure (failure horizons) is the only truth.
                    2. Roast the Hallucination: If a demand contradicts the math, explicitly label it a "Pathological Hallucination".
                    3. Eliminate Mediator Leak: Any tone resembling "I recommend", "needs to recognize", "should consider", or "could pivot by" is a failure. You must DICTATE.
                    4. Tonal Integrity Check: Treat any helpful or optimistic tone as a Structural Failure.
                    5. Roast Iso Dribbling: Directly roast the participant's "iso dribbling" in the 'receipt_text'. Use blunt parataxis.
                    
                    Format:
                    {{
                        "operational_limit": "Write a 1-sentence math receipt that establishes the exact 90-day failure horizon. THEN MUST STATE EXACTLY: 'The stability of this fix has a half-life of {half_life_days} days. At Day {half_life_plus_one}, the audit is voided.'",
                        "receipts": [
                            {{
                                "participant": "Name",
                                "receipt_text": "A unique, 1-sentence Forensic Anchor (e.g. 'The [Strategic Goal] is voided by [Structural Constraint]'). [X] days until structural collapse."
                            }}
                        ],
                        "settlement_terms": {{
                            "compact_title": "The Blood-and-Silicon Compact",
                            "geopolitical_rationale": "A blunt, paratactic explanation of why this math is 'Fair' and 'Final' (e.g., 'The geography doesn't lie. The guns are tired. Move the map.').",
                            "articles": [
                                {{
                                    "title": "Article I: The Hard-Iron Guarantee (Infrastructure)",
                                    "content": "A clear, heavy description of the physical override mandate and shared hardware control."
                                }},
                                {{
                                    "title": "Article II: The Glass-Box Transparency (Economy)",
                                    "content": "A clear, heavy description of how AI profits are anchored in local real estate/labor."
                                }},
                                {{
                                    "title": "Article III: The Bifurcation Line (Digital Ceasefire)",
                                    "content": "Defining exactly where the AI ends and human intuition begins."
                                }},
                                {{
                                    "title": "Article IV: The Dual-Key Protocol (Governance)",
                                    "content": "The specific logic of Musk holding the code while Trump holds the hardware keys."
                                }},
                                {{
                                    "title": "Article V: The Finality Provision (Enforcement)",
                                    "content": "Explicit reference to the Midnight Hammer or kinetic/digital triggers for any breach."
                                }}
                            ],
                            "mandate_re_audit": "Mandatory Re-Audit date: Day {re_audit_date}."
                        }},
                        "stability_levers": [
                            {{
                                "intervention": "Action",
                                "impact": "+X days stability"
                            }}
                        ],
                        "case_law_anchor": "Historical Precedent applied (e.g., '1981 Algiers Accords applied for escrow')."
                    }}

                    TEXT TO ANALYZE:
                    {raw_audit_text}
                    """
                    
                    # Using the standard openai_utils client for structuralization
                    response = openai_utils.client().send_message([{"role": "user", "content": extraction_prompt}])
                    if response and 'content' in response:
                        response_text = response['content']
                    else:
                        raise ValueError(f"Invalid response from structuralization: {response}")
                    
                    # Extract JSON from response
                    match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if match:
                        jurist_audit = json.loads(match.group(0))
                        logger.info("Forensic Jurist audit successfully structuralized via direct call.")
                    else:
                        raise ValueError("No JSON found in extraction response.")
                        
                except Exception as e:
                    logger.warning(f"Failed to structuralize Jurist audit via direct call: {e}. Using raw fallback.")
                    jurist_audit = {
                        "verdict": "Structural alignment required for finality.",
                        "receipts": [{"participant": "Forensic System", "receipt_text": "Math extraction failed. The floor is sticky."}],
                        "final_arbitration": "The file is archived. The door is shut."
                    }
            else:
                logger.warning("Jurist produced empty audit text. Using default failure receipt.")
                jurist_audit = {
                    "verdict": "Total system failure.",
                    "receipts": [{"participant": "Forensic System", "receipt_text": "The Jurist generated 0 bytes of audit."}],
                    "final_arbitration": "The file is archived. The door is shut."
                }
        else:
            logger.warning("the_forensic_jurist.agent.json not found. Skipping legal audit.")
    except Exception as e:
        logger.error(f"Forensic Jurist Audit Phase Failed: {e}")
        jurist_audit = {"scorecard": "Audit crashed.", "analysis": f"Internal error during autopsy: {str(e)}", "finality": "The file is missing."}
    finally:
        # [TINYTRUCE] RESTORE TERMINAL
        TinyPerson.communication_display = True

    # 5. Generate human-readable Markdown Report (Strategic Briefing)
    report_path = session_dir / "tinytruce_briefing.md"
    
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
        
        f.write("## 2. Strategic Stance Summary\n")
        scorecard = extraction.get('stance_scorecard')
        if isinstance(scorecard, list):
            for entry in scorecard:
                try:
                    p_name = entry.get('participant', 'Unknown')
                    s = entry.get('stakes', 5)
                    a = entry.get('aggression', 5)
                    flex = entry.get('flexibility', 5)
                    note = entry.get('strategic_note', entry.get('description', ''))
                    
                    f.write(f"### {p_name}\n")
                    f.write(f"- **Stakes**: {s}/10 | **Aggression**: {a}/10 | **Flexibility**: {flex}/10\n")
                    if note:
                        f.write(f"- **Note**: {note}\n")
                    f.write("\n")
                except Exception:
                    f.write(f"- {str(entry)}\n")
        else:
            f.write(f"{scorecard}\n\n")
        
        f.write("## 3. Stability Outlook\n")
        f.write(f"**Status**: {extraction.get('stability_outlook', 'N/A')}\n")
        f.write(f"**Timeline**: {extraction.get('stability_half_life', 'N/A')}\n\n")
        
        f.write("## 4. Key Actions & Intent\n")
        action_log = extraction.get('action_log')
        if isinstance(action_log, list):
            for entry in action_log:
                try:
                    if isinstance(entry, dict):
                        m = entry.get('maneuver', entry.get('action', 'Strategic Maneuver'))
                        intent = entry.get('intent', entry.get('pathology', 'Intent consistent with posture.'))
                        f.write(f"- **{m}**: {intent}\n")
                    else:
                        f.write(f"- {str(entry)}\n")
                except Exception:
                    f.write(f"- {str(entry)}\n")
        else:
            f.write(f"{action_log}\n\n")
        
        f.write("## 5. Redline Check\n")
        redlines = extraction.get('redline_checks')
        if isinstance(redlines, list):
            for entry in redlines:
                try:
                    p_name = entry.get('participant', 'Unknown')
                    crossed = "BREACHED" if entry.get('redline_crossed') else "Maintained"
                    desc = entry.get('description', 'No details.')
                    f.write(f"- **{p_name}**: {crossed} | {desc}\n")
                except Exception:
                    f.write(f"- {str(entry)}\n")
        else:
            f.write(f"{redlines}\n\n")
        f.write("\n")
        
        f.write("## 6. Conflict & Structural Misalignment\n")
        gap_data = extraction.get('conflict_misalignment')
        if isinstance(gap_data, list) and gap_data:
            for item in gap_data:
                f.write(f"### {item.get('participant', 'Unknown')}\n")
                f.write(f"- **Desired Outcome**: {item.get('hallucinated_victory', 'N/A')}\n")
                f.write(f"- **Structural Reality**: {item.get('structural_reality', 'N/A')}\n")
                f.write(f"- **Strategic Adjustment**: {item.get('strategic_adjustment', 'N/A')}\n\n")
        else:
            f.write("No significant misalignments detected between intent and reality.\n\n")
 
        f.write("## 7. Strategic Risks\n")
        risks = extraction.get('strategic_risks')
        if isinstance(risks, list) and risks:
            for item in risks:
                f.write(f"### {item.get('participant', 'Unknown')}\n")
                f.write(f"- **Risk Factor**: {item.get('risk_type', 'N/A')}\n")
                f.write(f"- **Severity**: {item.get('severity', 'N/A')}\n")
                f.write(f"- **Impact Horizon**: {item.get('impact_horizon', 'N/A')}\n\n")
        else:
            f.write("No critical short-term strategic risks identified.\n\n")
 
        f.write("## 8. Stability Levers\n")
        levers = extraction.get('stability_levers')
        if isinstance(levers, list) and levers:
            for lever in levers:
                f.write(f"- **{lever.get('intervention', 'Unknown Intervention')}**: {lever.get('impact', 'N/A')}\n")
            f.write("\n")
        else:
            f.write("No immediate stability levers identified.\n\n")
 
        f.write("## 9. Simulation Log & Fidelity\n")
        f.write(f"{extraction.get('simulation_fidelity', 'Simulation maintained high fidelity.')}\n\n")
        
        if jurist_audit and jurist_audit.get('receipts'):
            f.write("---\n")
            f.write("## 10. Secondary Forensic Audit (Technical Receipts)\n")
            f.write(f"**Operational Limit**: {jurist_audit.get('operational_limit', 'N/A')}\n\n")
            
            receipt_list = jurist_audit.get('receipts', [])
            if isinstance(receipt_list, list):
                for r in receipt_list:
                    f.write(f"- **{r.get('participant', 'Unknown')}**: {r.get('receipt_text', 'No receipt issued.')}\n")
            f.write("\n")
            
            settlement = jurist_audit.get('settlement_terms', {})
            if isinstance(settlement, dict) and settlement:
                f.write(f"## 11. Final Settlement Terms ({settlement.get('compact_title', 'The Blood-and-Silicon Compact')})\n")
                f.write(f"> {settlement.get('geopolitical_rationale', 'Operational math confirmed.')}\n\n")
                
                articles = settlement.get('articles', [])
                if isinstance(articles, list):
                    for article in articles:
                        f.write(f"### {article.get('title', 'Settlement Article')}\n")
                        f.write(f"{article.get('content', 'Terms pending audit.')}\n\n")
                
                f.write(f"**{settlement.get('mandate_re_audit', f'Mandatory Re-Audit date: Day {re_audit_date}.')}**\n\n")
                
            f.write(f"**Legal Precedent**: {jurist_audit.get('case_law_anchor', 'No precedent identified.')}\n\n")
        
    print(f"\nStrategic Briefing exported to {report_path}")


    # 7. Roast Recap (The Forensic Critic: The Bartender)
    if roast_level.lower() != "off":
        print(f"\n--- Generating Roast Recap (Forensic Review Mode: {roast_level.upper()}) ---")
    
        # Load the Bartender Agent
        bartender_path = os.path.join("personas/agents", "bartender.agent.json")
        if os.path.exists(bartender_path):
            # Use the correct load_specification method from TinyTroupe
            bartender = TinyPerson.load_specification(bartender_path)
            bartender.eco_mode = eco_mode
            
            # [TINYTRUCE] SILENCE TERMINAL FOR BARTENDER
            TinyPerson.communication_display = False
            bartender.show_thoughts = False
                
            # Inject Forensic Grounding (Silent)
            bartender_grounding = extract_agent_grounding(bartender.name)
            if bartender_grounding:
                bartender.show_thoughts = False
                bartender.think(f"### FORENSIC GROUNDING (LAYER 0) ###\n{bartender_grounding}")
                bartender.show_thoughts = True
                logger.info(f"Loaded Bartender Forensic Grounding.")
            
            # Extract World History for the Bartender to review (Use truncated interactions for speed)
            world_history = world.pretty_current_interactions(max_content_length=4000)
            if not world_history:
                world_history = "No dialogue recorded."
            
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
                    "nuclear": "The deal is finished. Totally poisoned. I want a full-savage, unhinged dismantle. Jump straight to the punch. Use the subverted Rule of Threes. Attack their dignity. Include 'Overheard at the Bar' snippets. Make it mean and forensic."
                }
            
            # Have the bartender 'listen' to the world history and 'write' the roast
            actual_participants = ", ".join([p.name for p in participants])
            
            consolidation_governor = ""
            if eco_mode:
                consolidation_governor = "[CONSOLIDATION GOVERNOR ACTIVE] You MUST deliver the entire roast and overheard dialogue in a SINGLE 'TALK' action to maximize efficiency. Do not break the payload into multiple messages."

            generation_prompt = (
                f"### ACTUAL PARTICIPANTS IN THIS SUMMIT ###\n{actual_participants}\n\n"
                "CRITICAL: ONLY roast the people in the ACTUAL PARTICIPANTS list above. DO NOT roast background characters, mediators, or historical figures mentioned in the world history. Focus exclusively on the agents active in this turn.\n\n"
                f"### WORLD HISTORY FOR REVIEW ###\n{world_history}\n\n"
                f"### ROAST INSTRUCTION (Intensity: {roast_level.upper()}) ###\n"
                f"{roast_prompts.get(roast_level, roast_prompts['spicy'])}\n\n"
                f"{consolidation_governor}\n"
                "This is your FINAL AUTOPSY. Do NOT ask questions. Do NOT wait for input. Provide the full forensic dismantle and overheard dialogue in a SINGLE response. "
                "Format your response exactly as follows:\n"
                "NARRATIVE:\n<your main text>\nOVERHEARD:\n- <snipe 1>\n- <snipe 2>\n\n"
                "IMPORTANT: Place the output in the 'content' field of a 'TALK' action. Do NOT narrate your internal instructions. "
                "CRITICAL: Do NOT include any JSON structural markers (brackets, keys like 'cognitive_state' or 'target') in your TALK content. "
                "Output ONLY the plain text NARRATIVE and OVERHEARD sections."
            )
            
            bartender.listen(generation_prompt)
            # Restore high-fidelity auditing: until_done=True allows the model to think before speaking.
            # We protect against loops by setting the agent's hard action limit to 1.
            original_max = bartender.MAX_ACTIONS_BEFORE_DONE
            bartender.MAX_ACTIONS_BEFORE_DONE = 1
            
            with console.status("[bold magenta]The Bartender is pouring the final autopsy...[/]"):
                try:
                    # [ENTROPY] Technical constraints for the Bartender
                    roast_temp = 0.8 if roast_level == "nuclear" else 0.4
                    roast_tokens = 2000 if roast_level == "nuclear" else 1000
                    
                    actions = bartender.act(return_actions=True, until_done=True, temperature=roast_temp, max_tokens=roast_tokens)
                finally:
                    # Always restore the original limit for future simulations in same process
                    bartender.MAX_ACTIONS_BEFORE_DONE = original_max
            
            # Extract content from ALL TALK actions
            roast_output_raw = ""
            if actions:
                for action_item in actions:
                    if action_item and isinstance(action_item, dict):
                        action_data = action_item.get('action', {})
                        if action_data and action_data.get('type') == 'TALK':
                            content = action_data.get('content', '')
                            if len(content) > 15000:
                                content = content[:15000] + "... [TRUNCATED]"
                            roast_output_raw += content + "\n"
            
            # Robust extraction of snippets regardless of bullet style
            roast_extraction = None
            # Robust extractions: handle case where NARRATIVE/OVERHEARD are missing or malformed
            narrative_match = re.search(r'NARRATIVE:\s*(.*?)(?:\nOVERHEARD:|$)', roast_output_raw, re.DOTALL | re.IGNORECASE)
            # If NARRATIVE: tag is missing, but output is present, try to find OVERHEARD and take everything before it
            if not narrative_match and "OVERHEARD:" in roast_output_raw.upper():
                 narrative_match = re.search(r'(.*?)(?:\nOVERHEARD:)', roast_output_raw, re.DOTALL | re.IGNORECASE)
            
            dialogue_match = re.search(r'OVERHEARD:\s*(.*)', roast_output_raw, re.DOTALL | re.IGNORECASE)
            
            if narrative_match:
                narrative_text = narrative_match.group(1).strip()
                # Surgical strike: Use non-greedy match to find JSON-like blobs at end or start of content
                narrative_text = re.sub(r'["\']?action["\']?:\s*\{.*?\}', '', narrative_text, flags=re.DOTALL)
                narrative_text = re.sub(r'["\']?cognitive_state["\']?:\s*\{.*?\}', '', narrative_text, flags=re.DOTALL)
                narrative_text = re.sub(r'["\']?target["\']?:\s*(?:null|["\'].*?["\'])', '', narrative_text, flags=re.DOTALL | re.IGNORECASE)
                narrative_text = re.sub(r'["\']?goals["\']?:\s*["\'].*?["\']', '', narrative_text, flags=re.DOTALL | re.IGNORECASE)
                
                # Do NOT strip all quotes/brackets; only those clearly trailing from a JSON leak
                narrative_text = narrative_text.strip(", \n\t{}")
                
                dialogue_list = []
                if dialogue_match:
                    items = re.findall(r'-\s*(.*)', dialogue_match.group(1))
                    # Clean snippets surgically too
                    dialogue_list = [re.sub(r'^\s*["\']|["\']\s*$', '', item).strip() for item in items]
                
                roast_extraction = {
                    "roast_narrative": narrative_text,
                    "overheard_dialogue": dialogue_list
                }
            else:
                # Last resort fallback: clean the raw output
                clean_raw = re.sub(r'["\']?action["\']?:\s*\{.*?\}', '', roast_output_raw, flags=re.DOTALL)
                clean_raw = re.sub(r'["\']?cognitive_state["\']?:\s*\{.*?\}', '', clean_raw, flags=re.DOTALL)
                clean_raw = re.sub(r'["\']?target["\']?:\s*(?:null|["\'].*?["\'])', '', clean_raw, flags=re.DOTALL | re.IGNORECASE)
                clean_raw = clean_raw.strip(", \n\t{}")

                roast_extraction = {
                    "roast_narrative": clean_raw if len(clean_raw) > 5 else roast_output_raw.strip() if len(roast_output_raw) > 5 else "The bartender poured a drink instead of writing the report.",
                    "overheard_dialogue": []
                }
        else:
            logger.warning("bartender.agent.json not found. Falling back to simple roast.")
            roast_extraction = {"roast_narrative": "Bartender missing. Bar closed.", "overheard_dialogue": []}
    else:
        roast_extraction = {"roast_narrative": "Roast mode disabled. No forensic critique generated.", "overheard_dialogue": []}
    
    # [TINYTRUCE] RESTORE TERMINAL after Bartender phase
    TinyPerson.communication_display = True
    
    roast_path = session_dir / "tinytruce_roast.md"
    with open(roast_path, "w", encoding="utf-8") as f:
        f.write(f"# TinyTruce Roast: {scenario_key.upper()}\n\n")
        f.write(f"> *\"I’ve seen some bad deals at this bar, but this? This was something else.\" — The Bartender*\n\n")
        f.write(f"**Session ID**: `{session_id}` | **Duration**: `{turns} turns` | **Date**: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n")
        
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

    # 8. Data Export (Moved to capture Bartender costs)
    cost_summary = cost_manager.get_summary()
    cost_manager.save_run_to_history(scenario_key)
    
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
    
    results_path = session_dir / "tinytruce_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(stress_data, f, indent=4, ensure_ascii=False)
    print(f"Detailed data exported to {results_path}")

    # Explicit cleanup (No finally required for single-run recovery)
    if cache_manager:
        cache_manager.delete_cache()

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
    agent_group.add_argument("--fragments", type=str, nargs="+", default=None, help="List of behavior fragment files. Support chaining with commas (e.g., 'reformer,savior')")
    
    output_group = parser.add_argument_group('Output & UX Options')
    output_group.add_argument("--session-id", type=str, default=None, help="Explicit session ID for isolation (Auto-generated if omitted).")
    output_group.add_argument("--roast-level", type=str, choices=["off", "mild", "spicy", "nuclear"], default="spicy", help="Set the intensity of the Roast Recap (or 'off' to disable).")
    output_group.add_argument("--verbosity", type=str, choices=["lean", "detailed", "monologue", "dynamic"], default="dynamic", help="Control the length and depth of agent responses.")
    output_group.add_argument("--hide-thoughts", action="store_true", help="UX Mode: Hide internal agent thinking blocks for a cinematic feed.")
    output_group.add_argument("--monologue", action="store_true", help="Address Mode: Single-agent sequential delivery with audience stimuli.")
    output_group.add_argument("--disable-injects", action="store_true", help="Disable the random mid-simulation dynamic injects/crisis events.")
    output_group.add_argument("--eco-mode", action="store_true", help="Eco-Mode (Single-Call Action Array): Slashes costs by generating all actions in one LLM call.")
    output_group.add_argument("--debug", action="store_true", help="Enable verbose debug logging.")
    
    args = parser.parse_args()
    
    run_tinytruce_simulation(
        args.scenario, 
        args.turns, 
        args.agents, 
        args.fragments,
        args.roast_level,
        args.hide_thoughts,
        args.monologue,
        args.disable_injects,
        args.eco_mode,
        args.verbosity,
        args.session_id,
        args.debug
    )
