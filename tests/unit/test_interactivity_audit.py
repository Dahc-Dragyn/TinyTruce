import sys
import os
import json
import logging
import datetime

# FORCE UTF-8 for entire process output
if sys.platform == "win32":
    import _locale
    _locale._getdefaultlocale = (lambda *args: ['en_US', 'utf8'])

# Suppress all tinytroupe warnings at ROOT level
logging.basicConfig(level=logging.ERROR)
logging.getLogger("tinytroupe").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)

# FORCE LOCAL IMPORT
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld
from tinytroupe.cost_manager import cost_manager
from tinytruce_sim import GeopoliticalCacheManager

# DISABLE RICH TERMINAL DISPLAY
TinyPerson.communication_display = False

def run_interactivity_audit():
    """
    Diagnostic script to verify agent-to-agent communication.
    Includes Gemini Cache integration and Billing updates.
    Ensures safe resource cleanup.
    """
    report_path = os.path.join(project_root, "audit_report_v9.txt")
    
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write("--- INITIATING INTERACTIVITY AUDIT (3 AGENTS) ---\n")
        rf.write(f"Started at: {datetime.datetime.now()}\n\n")

    print("\nStarting Interactivity Audit (check audit_report_v9.txt for progress)...")
    
    cache_id = None
    cache_manager = None

    try:
        # 1. Setup real agents with full specifications
        agents_dir = os.path.join(project_root, "personas", "agents")
        trump = TinyPerson.load_specification(os.path.join(agents_dir, "donald_trump.agent.json"), new_agent_name="Donald Trump")
        putin = TinyPerson.load_specification(os.path.join(agents_dir, "vladimir_putin.agent.json"), new_agent_name="Vladimir Putin")
        elon = TinyPerson.load_specification(os.path.join(agents_dir, "elon_musk.agent.json"), new_agent_name="Elon Musk")
        
        participants = [trump, putin, elon]
        world = TinyWorld("Test Audit", participants)
        
        # 2. Gemini Cache Integration
        context_bundle = ""
        for p in participants:
            context_bundle += f"### {p.name} ###\n{json.dumps(p._persona, indent=2)}\n\n"
        
        # Force cache threshold
        if len(context_bundle) < 4000:
             context_bundle += " " * (4000 - len(context_bundle))

        cache_manager = GeopoliticalCacheManager(context_bundle, session_id="interactivity_audit_v9")
        cache_id = cache_manager.create_cache()
        
        if cache_id:
            os.environ["TINYTRUCE_CURRENT_CACHE"] = cache_id
            with open(report_path, "a", encoding="utf-8") as rf:
                rf.write(f"[CACHE]: Active Context Cache '{cache_id}' verified.\n")

        # 3. Execution Phase
        def prompt_agent(agent, others_names):
            prompt = (
                f"You are {agent.name}. You are in a heated debate with {', '.join(others_names)}.\n"
                f"MANDATORY: You MUST explicitly address {others_names[0]} or {others_names[1]} by name in your response.\n"
                "Challenge their specific claims from the previous turns. Do not monologue."
            )
            agent.listen_and_act(prompt)

        # Turn 1: Trump opening statement
        with open(report_path, "a", encoding="utf-8") as rf: rf.write("\n[Turn 1] Trump opening statement...\n")
        trump.listen_and_act("Start the debate about AI sovereignty and resource pincer maneuvers.")
        
        # Turn 2: Putin responds to Trump
        with open(report_path, "a", encoding="utf-8") as rf: rf.write("\n[Turn 2] Putin responding...\n")
        prompt_agent(putin, ["Donald Trump", "Elon Musk"])
        
        # Turn 3: Elon responds to both
        with open(report_path, "a", encoding="utf-8") as rf: rf.write("\n[Turn 3] Elon responding...\n")
        prompt_agent(elon, ["Donald Trump", "Vladimir Putin"])
        
        # 4. Audit the Dialogue
        with open(report_path, "a", encoding="utf-8") as rf: rf.write("\n--- AUDIT RESULTS ---\n")
        dialogue_dump = []

        for agent in participants:
            all_content = ""
            for msg in agent.current_messages:
                content = msg.get('content')
                if isinstance(content, dict):
                    action_data = content.get('action') or {}
                    talk = action_data.get('content', '')
                    if talk: all_content += " " + str(talk)
                    actions_list = content.get('actions')
                    if actions_list and isinstance(actions_list, list):
                        for a in actions_list:
                            if isinstance(a, dict) and a.get('type') == 'TALK':
                                all_content += " " + str(a.get('content', ''))
                elif isinstance(content, str):
                    if "messages here" not in content and "must generate" not in content:
                        all_content += " " + content
            
            dialogue_dump.append(all_content)
            clean_text = all_content.replace("\n", " ")[:200] + "..." if all_content else "[NO DIALOGUE DETECTED]"
            with open(report_path, "a", encoding="utf-8") as rf:
                rf.write(f"[{agent.name}] Memory Dump: {clean_text}\n")

        # Cross-Pollination Check
        rivals = {
            "Donald Trump": ["Vladimir", "Putin", "Elon", "Musk"],
            "Vladimir Putin": ["Donald", "Trump", "Elon", "Musk"],
            "Elon Musk": ["Donald", "Trump", "Vladimir", "Putin", "Vlad"]
        }

        def check_mention(text, target_list):
            text_lower = text.lower()
            return any(name.lower() in text_lower for name in target_list)

        results = []
        for i, agent in enumerate(participants):
            mentions_rival = check_mention(dialogue_dump[i], rivals[agent.name])
            results.append(mentions_rival)
            with open(report_path, "a", encoding="utf-8") as rf:
                rf.write(f"{agent.name} addressed a rival: {'OK' if mentions_rival else 'MISSING'}\n")

        # 5. Billing Export
        with open(report_path, "a", encoding="utf-8") as rf: rf.write("\n--- UPDATING BILLING LEDGER ---\n")
        cost_manager.save_run_to_history("interactivity_audit_v9")
        with open(report_path, "a", encoding="utf-8") as rf: rf.write("Billing ledger updated.\n")

        # FINAL DETERMINATION
        if all(results[1:]):
            with open(report_path, "a", encoding="utf-8") as rf: rf.write("\nINTERACTIVITY AUDIT: PASSED\n")
            print("Audit complete: PASSED.")
            return True
        else:
            with open(report_path, "a", encoding="utf-8") as rf: rf.write("\nINTERACTIVITY AUDIT: FAILED\n")
            print("Audit complete: FAILED.")
            return False

    except Exception as e:
        with open(report_path, "a", encoding="utf-8") as rf:
            rf.write(f"\nCRITICAL ERROR: {str(e)}\n")
        print(f"Audit crashed: {str(e)}")
        return False

    finally:
        # 6. Guaranteed Cleanup
        if cache_manager and cache_id:
            with open(report_path, "a", encoding="utf-8") as rf: rf.write(f"\n[CLEANUP]: Purging Context Cache {cache_id}...\n")
            cache_manager.delete_cache()
            if "TINYTRUCE_CURRENT_CACHE" in os.environ:
                del os.environ["TINYTRUCE_CURRENT_CACHE"]

if __name__ == "__main__":
    run_interactivity_audit()
