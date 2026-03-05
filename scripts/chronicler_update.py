import os
import sys
import json
import logging
import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import tinytruce_sim as sim
from tinytroupe.agent import TinyPerson, SituationRoomFaculty

from tinytroupe.cost_manager import cost_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chronicler_update")

# Root path for all relative project assets
ROOT = Path(__file__).parent.parent.absolute()

class ChroniclerUpdate:
    def __init__(self, output_file=None):
        if output_file is None:
            # Default location in project root
            self.output_file = ROOT / "data" / "facts" / "daily-intelligence.2026.txt"
        else:
            self.output_file = Path(output_file).absolute()
            
        self.agent = None
        self.situation_room = None
        
    def initialize(self):
        logger.info(f"Initializing Chronicler Agent (Running from: {ROOT})...")
        # Ensure we're in the project root to fix config.ini and path lookup issues
        os.chdir(ROOT)
        
        # Reset costs at start
        cost_manager.reset()
        
        agent_path = ROOT / "personas" / "agents" / "chronicler.agent.json"
        
        if not agent_path.exists():
            raise FileNotFoundError(f"[FATAL]: Could not find agent at {agent_path}")
            
        self.agent = TinyPerson.load_specification(str(agent_path))
        
        # Add Situation Room faculty
        self.situation_room = SituationRoomFaculty()
        self.agent.add_mental_faculty(self.situation_room)
        
    def harvest_and_synthesize(self):
        logger.info("Harvesting news from Situation Room...")
        self.agent.show_thoughts = True # Force visibility during update
        
        # 1. Get Breaking Alerts
        logger.info("Requesting Breaking Alerts...")
        self.agent.think("System Command: Execute GET_ALERTS now. I must see the high-signal wire (Severity 4-5).")
        self.agent.act(until_done=True)
        
        # 2. Consolidated Scenario Search
        logger.info("Performing Consolidated Scenario Search...")
        scenario_query = (
            "Geopolitical Status March 2026: AI Sovereignty Trends, "
            "Petrodollar Energy Shifts, US Domestic Stability (SOTU), "
            "Vatican Cyber-Schism, Ukraine War Frontlines, "
            "Middle East Reset, Hindu Kush Open War, and Venezuela Post-Maduro Transition"
        )
        self.agent.think(f"System Command: Execute SEARCH_NEWS for '{scenario_query}'.")
        self.agent.act(until_done=True)

        # 3. High-Signal Kinetic/Forensic Search
        logger.info("Performing Forensic Kinetic Search...")
        kinetic_keywords = (
            "geopolitical kinetic flashpoints: assassination, nuclear, strike, casualties, "
            "blockade, insurrection, annexation, cyber-sabotage, mobilization, asymmetric, radicalization"
        )
        self.agent.think(f"System Command: Execute SEARCH_NEWS for '{kinetic_keywords}'. "
                         "I need raw tactical signal for these high-alert triggers.")
        self.agent.act(until_done=True)
        
        # Final ingestion thought
        self.agent.think("I have the unified kinetic and scenario wire. I will now synthesize the 'Daily Intelligence Briefing'.")
        self.agent.act(until_done=True)

        logger.info("Synthesizing Daily Intelligence Briefing...")
        # Force a summary thought that aggregates previous findings
        self.agent.think("ACTION REQUIRED: You must now produce the FULL 'Daily Intelligence Briefing'.\n\n"
                         "RULES:\n"
                         "1. DO NOT give meta-commentary like 'The report is prepared'.\n"
                         "2. DO NOT use placeholders.\n"
                         "3. YOU MUST output the actual content: The Highlights, the Scenario Grounds (AI, Energy, Domestic, Ukraine, Middle East, Hindu Kush, Venezuela).\n"
                         "4. CITE the wire for specific signal.\n\n"
                         "YOUR VERY NEXT ACTION MUST BE 'TALK' CONTAINING THE FULL REPORT.")
        
        # Keep acting until a TALK action with significant content is produced
        max_attempts = 2
        report = ""
        for attempt in range(max_attempts):
            actions = self.agent.act(until_done=True, return_actions=True)
            for action_content in actions:
                if action_content['action']['type'] == 'TALK':
                    content = action_content['action']['content']
                    # Ensure it's not meta-commentary
                    if len(content) > 300 and "Daily Intelligence Briefing" in content:
                        report = content
                        break
            if report:
                break
            self.agent.think("FAILURE: The previous output was either too short or meta-commentary. "
                             "I COMMAND YOU to output the FULL Geopolitical Report now. Mention AI, Petrodollar, and Conflict clusters.")
        
        return report

    def commit(self, report):
        if not report:
            logger.error("No report generated. Skipping commit.")
            return
            
        logger.info(f"Committing briefing to {self.output_file}...")
        
        # Get costs
        costs = cost_manager.total_cost
        
        header = f"### DAILY INTELLIGENCE BRIEFING: {datetime.date.today().isoformat()} ###\n"
        header += "SOURCE: THE CHRONICLER // FORENSIC INTELLIGENCE DESK\n"
        header += f"COMMISSIONING COST: ${costs:.4f}\n"
        header += "STABILITY LEVEL: HIGH\n\n"
        
        full_content = header + report
        
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        logger.info(f"Commit successful. Total Session Cost: ${costs:.4f}")
        summary = cost_manager.get_summary()
        logger.info(f"Usage Summary: {summary['total_input_tokens']} in, {summary['total_output_tokens']} out")
        
        # Save to permanent billing history
        cost_manager.save_run_to_history("Chronicler Geopolitical Update")


if __name__ == "__main__":
    update = ChroniclerUpdate()
    update.initialize()
    report = update.harvest_and_synthesize()
    update.commit(report)
