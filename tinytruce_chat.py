import os
import sys
import json
import logging
import argparse
import uuid
import datetime
import random
from pathlib import Path

# Set tinytroupe log level to DEBUG for this session
logging.getLogger("tinytroupe").setLevel(logging.DEBUG)

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.prompt import Prompt

# Reuse core logic from tinytruce_sim
import tinytruce_sim as sim
from tinytroupe.agent import TinyPerson, SituationRoomFaculty
from tinytroupe.environment import TinyWorld

# Configure logs
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("tinytruce_chat")
console = Console()

class TinyTruceInterrogator:
    def __init__(self, agent_file, fragment_names=None, scenario_file=None, session_id=None, use_cache=True):
        self.agent_file = agent_file
        self.fragment_names = fragment_names or ["preserver.fragment.json"]
        self.scenario_file = scenario_file
        self.session_id = session_id or f"interrogate_{uuid.uuid4().hex[:8]}"
        self.use_cache = use_cache
        self.agent = None
        self.cache_manager = None
        self.scenario_data = None
        self.session_dir = Path(f"DOCUMENTS/runs/{self.session_id}")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # UI Tuning
        TinyPerson.MAX_ACTIONS_BEFORE_DONE = 2
        TinyPerson.communication_display = False
        
    def initialize(self):
        console.print(f"[bold cyan]Initializing Interrogation Chamber...[/bold cyan]")
        
        # 0. Load Scenario if provided
        scenario_grounding = ""
        context_stimulus = ""
        if self.scenario_file:
            if not self.scenario_file.endswith(".json"):
                self.scenario_file = f"{self.scenario_file}.json"
            
            scenario_path = os.path.join("scenarios", self.scenario_file)
            if os.path.exists(scenario_path):
                with open(scenario_path, "r", encoding="utf-8") as f:
                    self.scenario_data = json.load(f)
                
                # Extract grounding
                payload = self.scenario_data.get("grounding_payload", [])
                for p in payload:
                    if os.path.exists(p):
                        with open(p, "r", encoding="utf-8") as gf:
                            scenario_grounding += f"\n### SCENARIO DATA: {Path(p).name} ###\n{gf.read()}\n"
                
                # Context
                context_stimulus = (
                    f"### SCENARIO: {self.scenario_data.get('world_name')} ###\n"
                    f"CONTEXT: {self.scenario_data.get('initial_broadcast')}\n"
                    f"INTERVENTION: {self.scenario_data.get('intervention')}\n"
                    f"FOCUS: {self.scenario_data.get('scenario_knowledge')}\n"
                )
        
        # 1. Reset costs
        sim.cost_manager.reset()
        
        # 2. Prepare Grounding Bundle for Cache
        world_facts_path = "data/facts/world-facts.2026.txt"
        daily_intel_path = "data/facts/daily-intelligence.2026.txt"
        
        global_grounding = ""
        if os.path.exists(world_facts_path):
            with open(world_facts_path, "r", encoding="utf-8") as f:
                global_grounding = f.read()
        
        if os.path.exists(daily_intel_path):
            with open(daily_intel_path, "r", encoding="utf-8") as f:
                daily_intel = f.read()
                global_grounding = f"### [CORE SHARED WORLD STATE (2026)] ###\n{global_grounding}\n\n{daily_intel}"
        
        global_grounding += scenario_grounding
        
        layer0_bundle = f"### GLOBAL SHARED WORLD STATE (2026) ###\n{global_grounding}\n\n"
        
        # 3. Load Agent
        agent_dir = "personas/agents"
        frag_dir = "personas/fragments"
        
        if not self.agent_file.endswith(".agent.json"):
            self.agent_file = f"{self.agent_file}.agent.json"
        
        agent_path = os.path.join(agent_dir, self.agent_file)
        
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_data = json.load(f)
        actual_name = agent_data["persona"].get("full_name", agent_data["persona"]["name"])
        
        self.agent = TinyPerson.load_specification(agent_path, new_agent_name=actual_name)
        self.agent._fragment_redlines = []
        
        # Load Fragments
        self.load_fragments(self.fragment_names)
        
        # [TINYTRUCE] Active Intelligence Faculty
        self.situation_room = SituationRoomFaculty()
        self.agent.add_mental_faculty(self.situation_room)
        
        # Agent Grounding
        grounding = sim.extract_agent_grounding(self.agent.name)
        if grounding:
            layer0_bundle += f"### {self.agent.name} FORENSIC PROFILE ###\n{grounding}\n\n"
            self.agent.think(f"### LAYER 0: GROUNDING ###\n{grounding}")
        
        self.agent.think(f"### GLOBAL INTELLIGENCE (2026) ###\n{global_grounding}")
        
        if context_stimulus:
            self.agent.think(f"### SCENARIO CONTEXT ###\n{context_stimulus}")
            console.print(f"[bold yellow]Scenario Context Injected: {self.scenario_data.get('world_name')}[/bold yellow]")

        self.agent.think("### INTERROGATION PROTOCOL ###\n"
             "You are in a secure interrogation room. A 'User' is questioning you.\n"
             "RULES:\n"
             "1. Your primary world state is defined by the 'GLOBAL INTELLIGENCE' (including Chronicler updates).\n"
             "2. You MUST respond to every stimulus from the 'User'. Use 'TALK' for your final response.\n"
             "3. Your 'TALK' content must be 10/10 forensic fidelity to your persona.\n"
             "4. If you lack specific data for a theater in the Chronicler update, use your 'Situation Room' tools (SEARCH_NEWS, GET_ALERTS) for a 'Deep Search'.\n"
             "5. Do not guess on current theater status if the Situation Room is available.\n"
             "6. Keep your turn to 1-4 actions if queries are needed. Always end with 'DONE'.")
        
        # 4. Mandatory Cache Setup
        if self.use_cache:
            self.cache_manager = sim.GeopoliticalCacheManager(layer0_bundle, session_id=self.session_id)
            try:
                cache_id = self.cache_manager.create_cache()
                if cache_id:
                    os.environ["TINYTRUCE_CURRENT_CACHE"] = cache_id
                    console.print(f"[bold green]Gemini Cache Active for {self.agent.name}: {cache_id}[/bold green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Cache creation failed: {e}[/yellow]")

        return True

    def load_fragments(self, fragment_names):
        frag_dir = "personas/fragments"
        for f_name in fragment_names:
            f_name = f_name.strip()
            if not f_name.endswith(".fragment.json"):
                f_name = f_name + ".fragment.json"
            f_path = os.path.join(frag_dir, f_name)
            if os.path.exists(f_path):
                with open(f_path, "r", encoding="utf-8") as ff:
                    f_data = json.load(ff)
                    new_redlines = f_data.get("persona", {}).get("redlines", [])
                    self.agent._fragment_redlines.extend(new_redlines)
                self.agent.import_fragment(f_path)
                
                # [TINYTRUCE] Redline Enforcement
                if new_redlines:
                    redline_prompt = "### [BANNED BEHAVIORS: FRAGMENT REDLINES] ###\n"
                    redline_prompt += "\n".join([f"- [CONSTRAIN]: {rl}" for rl in new_redlines])
                    redline_prompt += "\n\nCRITICAL: These are hard constraints. Violating these results in immediate tactical failure."
                    self.agent.think(redline_prompt)
                    
                console.print(f"[bold green]Fragment loaded: {f_name}[/bold green]")
            else:
                console.print(f"[bold red]Fragment not found: {f_name}[/bold red]")

    def interrogation_loop(self):
        console.print(f"\n[bold green]Interrogating: [cyan]{self.agent.name}[/bold green]")
        console.print("[dim]Commands: /fragment <name>, /clear (Prune Memory), /bye (Exit)[/dim]\n")
        
        while True:
            # 1. User Input
            user_input = Prompt.ask("[bold yellow]User[/bold yellow]")
            
            if user_input.lower() in ["exit", "quit", "/bye", "/exit"]:
                break
                
            if user_input.startswith("/"):
                self.handle_command(user_input)
                continue
            
            # 2. Reset News Quota for the turn
            self.situation_room.reset_quota()
            
            # 3. Contextualize Input with Situation Room Alerts
            tactical_keywords = ["objective", "theater", "achieved", "news", "wire", "ground truth", "operation"]
            personal_keywords = ["assassination", "dead", "killed", "captured", "status", "where is"]
            
            alerts = []
            if any(k in user_input.lower() for k in tactical_keywords):
                alerts.append("SITUATION ROOM: You have NO internal data for the current 2026 theater state. Verify the wire before you TALK.")
            
            if any(k in user_input.lower() for k in personal_keywords):
                alerts.append("ONTOLOGICAL SHOCK: Reports are circulating regarding your terminal status. Verify the wire to address these reports.")
            
            final_stimulus = user_input
            if alerts:
                alert_text = "\n".join([f"### [{a}] ###" for a in alerts])
                final_stimulus = f"{alert_text}\n\n[USER]: {user_input}"
            
            # MANDATORY REFLECTION: Enforce acknowledgment of user keywords
            acknowledgment_rule = (
                "\n\n### [CRITICAL FORENSIC RULE: REFLECTIVE MIRRORING] ###\n"
                f"You MUST explicitly use the user's keywords (specifically: '{user_input[:100]}') in your first sentence. "
                "Do NOT pivot to 'The Weave' or global intelligence until you have acknowledged the user's specific noun/subject. "
                "This is mandatory for realism. End your turn with 'DONE' immediately after 'TALK'."
            )
            final_stimulus += acknowledgment_rule
            
            self.agent.listen(final_stimulus, source="User")
            
            # 3. Agent Processes & Responds
            with Live(console=console, refresh_per_second=4) as live:
                live.update(f"[cyan]{self.agent.name} is formulating response...[/cyan]")
                
                # Prune memory to keep context clean
                sim.compress_agent_memory([self.agent], window_size=8, prune_count=4)
                
                # Respond
                action_items = self.agent.act(return_actions=True)
                
                # Display Results
                if action_items:
                    for item in action_items:
                        action = item.get('action')
                        if action:
                            type = action.get('type')
                            content = action.get('content')
                            
                            if type == 'TALK':
                                # UI Feedback for talking
                                cog_state = item.get('cognitive_state', {})
                                mood = cog_state.get('emotions', 'NEUTRAL')
                                intensity = float(cog_state.get('emotional_intensity', 0.5))
                                
                                mood_bar = sim.draw_mood_bar(self.agent.name, mood, intensity)
                                console.print(f"\n{mood_bar}")
                                console.print(Panel(content, title=f"{self.agent.name}", border_style="green"))
                            
                            if type == 'DONE':
                                break

            # 4. Heartbeat: Renew Cache if needed
            if self.cache_manager:
                self.cache_manager.renew_if_needed()

    def handle_command(self, cmd):
        parts = cmd.split(" ", 1)
        base_cmd = parts[0].lower()
        
        if base_cmd == "/clear":
            sim.compress_agent_memory([self.agent], window_size=0, prune_count=99)
            console.print("[bold green]Agent memory reset.[/bold green]")
        elif base_cmd == "/fragment":
            if len(parts) < 2:
                console.print("[bold red]Usage: /fragment <name>[/bold red]")
            else:
                f_name = parts[1].strip()
                self.load_fragments([f_name])
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")

    def cleanup(self):
        if self.cache_manager:
            self.cache_manager.delete_cache()
        console.print("[bold cyan]Interrogation session ended.[/bold cyan]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TinyTruce 1-on-1 Interrogator")
    parser.add_argument("--agent", default="kai_chen.agent.json", help="Agent JSON file")
    parser.add_argument("--fragments", nargs="+", default=None, help="Behavior fragments")
    parser.add_argument("--scenario", default=None, help="Scenario JSON for context")
    parser.add_argument("--session-id", help="Explicit session/cache ID")
    parser.add_argument("--no-cache", action="store_true", help="Disable context caching")
    
    args = parser.parse_args()
    
    # Interactive Fragment Selection if none provided
    fragments = args.fragments
    if not fragments:
        frag_dir = Path("personas/fragments")
        frag_pool = [f.name for f in frag_dir.glob("*.fragment.json")]
        if frag_pool:
            selected = sim.select_from_pool(frag_pool, "Behavior Fragment (Optional, Enter to skip)")
            if selected:
                fragments = [selected]
            else:
                fragments = []
    
    chat = TinyTruceInterrogator(
        agent_file=args.agent,
        fragment_names=fragments,
        scenario_file=args.scenario,
        session_id=args.session_id,
        use_cache=not args.no_cache
    )
    
    if chat.initialize():
        try:
            chat.interrogation_loop()
        except KeyboardInterrupt:
            pass
        finally:
            chat.cleanup()
