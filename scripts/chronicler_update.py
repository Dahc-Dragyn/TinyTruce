import os
import sys
import json
import logging
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

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
        
        # Force Native Gemini engine to bypass OpenAI adapter issues
        os.environ["TINYTRUCE_FORCE_NATIVE_LLM"] = "true"
        
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
        logger.info("Harvesting global kinetic news from Situation Room...")
        self.agent.show_thoughts = True # Force visibility during update
        
        # 1. Get Global High-Severity Alerts (MANDATORY START)
        logger.info("Requesting Global High-Severity Alerts...")
        self.agent.think("System Command: Execute GET_ALERTS. Prioritize Severity 4.5+ items across all theaters.")
        self.agent.act(until_done=True)
        
        # 2. Global Kinetic Probes (Multi-Source Harvesting)
        feed_clusters = [
            ("ISW/ACLED Frontlines", "missile strikes, artillery escalation, drone blitz, offensive operations, mobilization"),
            ("Reuters/AP Alerts", "assassinations, infrastructure sabotage, command center strikes, logistical failure"),
            ("State Media Narrative", "blockades, nuclear threats, asymmetric warfare, regime collapse, internal insurrection")
        ]
        
        for source_cluster, topics in feed_clusters:
            logger.info(f"Probing source cluster: {source_cluster}...")
            # We search globally, not by scenario, to capture the 'War Wire' signal cross-verified
            query = f"Global {source_cluster}: {topics}"
            self.agent.think(f"System Command: Execute SEARCH_NEWS for '{query}' from {source_cluster}. Focus on high-signal War News (Severity > 4.5).")
            self.agent.act(until_done=True)
            import time
            time.sleep(15) # Pace the requests to avoid Vertex AI 429 errors

        # 3. Quantitative Metrics Logic
        logger.info("Executing Quantitative Metrics Logic...")
        self.agent.think("I will now estimate the Kinetic and Economic Toll. I must identify: Estimated Casualty Counts, Infrastructure Damage (%), and Market Shocks (e.g., Oil/Gas price spikes).")
        self.agent.act(until_done=True)

        # 4. Structural Synthesis thought
        self.agent.think("I have the global tactical wire. I will now synthesize the **GLOBAL WAR WIRE BRIEFING**.")
        self.agent.act(until_done=True)

        logger.info("Synthesizing Global War Wire with Cross-Verification...")
        # Force a summary thought that aggregates previous findings with high-severity priority
        self.agent.think("ACTION REQUIRED: You must now produce the **'GLOBAL WAR WIRE: MARCH 2026'** report.\n\n"
                         "### GLOBAL WAR WIRE PROTOCOL ###\n"
                         "1. SEVERITY-FIRST: Start the report with the highest severity (Severity 5.0) items globally.\n"
                         "2. NO SILOS: Do not group by scenario (e.g. 'Ukraine'). Group by **TACTICAL IMPACT**.\n"
                         "3. TACTICAL FIDELITY: Describe specific weapon systems (e.g. 'Long-range drones', 'Pantsir-S2'), units, and damage assessments.\n"
                         "4. IMPACT ANALYSIS: For every event, explain the immediate kinetic or strategic consequence.\n"
                         "5. SOURCE DIVERSITY CHECK: For every Severity 4.5+ event, the Chronicler must check for corroboration across at least two sources.\n"
                         "6. BIAS REDUCTION: Explicitly flag state media reports as 'Unverified Narrative' if they contradict Reuters/AP ground truth.\n"
                         "7. TRAILING CONTEXT: Ensure the Global War Wire output uses the 'This follows...' logic to maintain a persistent timeline.\n"
                         "8. CITE everything from the wire.\n\n"
                         "YOUR VERY NEXT ACTION MUST BE 'TALK' CONTAINING THE FULL REPORT.")
        
        # Keep acting until a TALK action with significant content is produced
        max_attempts = 3
        report = ""
        for attempt in range(max_attempts):
            actions = self.agent.act(until_done=True, return_actions=True)
            for action_content in actions:
                if action_content['action']['type'] == 'TALK':
                    content = action_content['action']['content']
                    # Ensure it's a meaty tactical briefing
                    if len(content) > 800 and "GLOBAL WAR WIRE" in content.upper():
                        report = content
                        break
            if report:
                break
            self.agent.think("FAILURE: Too vague. I need the raw tactical pulse. "
                             "Mention specific strikes, sabotages, and fronts. Lead with the most severe signal. "
                             "I am paying for high-level tactical intelligence, not a news digest.")
        
        return report

    def commit(self, report):
        # Get costs
        costs = cost_manager.total_cost
        summary = cost_manager.get_summary()
        
        logger.info(f"Session Cost estimate: ${costs:.4f}")
        logger.info(f"Usage Summary: {summary['total_input_tokens']} in, {summary['total_output_tokens']} out")

        if not report:
            logger.error("No report generated. Skipping commit.")
            # Still save history if there was usage
            if costs > 0:
                cost_manager.save_run_to_history("Chronicler Geopolitical Update (FAILED)")
            return
            
        logger.info(f"Committing briefing to {self.output_file}...")
        
        header = f"### DAILY INTELLIGENCE BRIEFING: {datetime.date.today().isoformat()} ###\n"
        header += "SOURCE: THE CHRONICLER // FORENSIC INTELLIGENCE DESK\n"
        header += f"COMMISSIONING COST: ${costs:.4f}\n"
        header += "STABILITY LEVEL: HIGH\n\n"
        
        full_content = header + report
        
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        logger.info(f"Commit successful. Total Session Cost: ${costs:.4f}")
        
        # Save to permanent billing history
        cost_manager.save_run_to_history("Chronicler Geopolitical Update")


if __name__ == "__main__":
    update = ChroniclerUpdate()
    update.initialize()
    report = update.harvest_and_synthesize()
    update.commit(report)
