import os
import sys
import json
import logging
import datetime
import time
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
logger = logging.getLogger("us_iran_war_update")

# Root path for all relative project assets
ROOT = Path(__file__).parent.parent.absolute()

class USIranWarUpdate:
    def __init__(self, output_file=None):
        if output_file is None:
            # Default location in project root
            self.output_file = ROOT / "data" / "facts" / "us-iran-war-intelligence.2026.txt"
        else:
            self.output_file = Path(output_file).absolute()
            
        self.agent = None
        self.situation_room = None
        
    def initialize(self):
        logger.info(f"Initializing US-Iran War Desk (Running from: {ROOT})...")
        os.chdir(ROOT)
        
        # Force Native Gemini engine
        os.environ["TINYTRUCE_FORCE_NATIVE_LLM"] = "true"
        
        # Reset costs at start
        cost_manager.reset()
        
        agent_path = ROOT / "personas" / "agents" / "us_iran_war_desk.agent.json"
        
        if not agent_path.exists():
            raise FileNotFoundError(f"[FATAL]: Could not find agent at {agent_path}")
            
        self.agent = TinyPerson.load_specification(str(agent_path))
        
        # Add Situation Room faculty
        self.situation_room = SituationRoomFaculty()
        self.agent.add_mental_faculty(self.situation_room)
        
    def harvest_and_synthesize(self):
        logger.info("Harvesting Middle East theater news from Situation Room...")
        self.agent.show_thoughts = True # Force visibility during update
        
        # 1. Get High-Severity Alerts (MANDATORY START)
        logger.info("Requesting Middle East High-Severity Alerts...")
        self.agent.think("System Command: Execute GET_ALERTS. Prioritize items concerning Iran, Israel, the Gulf, and direct energy shocks.")
        self.agent.act(until_done=True)
        time.sleep(15)
        
        # 2. Middle East Direct Feed Harvest
        rss_url = "https://news.google.com/rss/search?q=US+Iran+Israel+war+Middle+East&hl=en-US&gl=US&ceid=US:en"
        logger.info(f"Fetching Middle East RSS feed from {rss_url}...")
        try:
            import requests
            import xml.etree.ElementTree as ET
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(rss_url, headers=headers, timeout=15)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            
            feed_items = []
            for item in root.findall('.//channel/item')[:15]:  # limit to top 15 to avoid context bloat
                title = item.find('title').text if item.find('title') is not None else 'No Title'
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else 'No Date'
                
                feed_items.append(f"- [{pub_date}] {title}")
                
            feed_text = "\n".join(feed_items)
            self.agent.think(f"### [OSINT MIDDLE EAST ESCALATION FEED] ###\n\n{feed_text}\n\nYou MUST use these specific, granular reports for your ESCALATION LADDER and REGIME COHESION metrics.")
            self.agent.act(until_done=True)
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Failed to fetch Middle East RSS feed: {e}")
            self.agent.think(f"### [SYSTEM ERROR] ###\nUnable to reach Middle East OSINT feed. Reason: {e}. Fallback to generic searching.")
            self.agent.act(until_done=True)

        # 3. Quantitative Metrics Logic
        logger.info("Executing US-Iran Quantitative Metrics Logic...")
        self.agent.think("I will now execute Escalation Ladder Mapping. I must calculate explicit 'Energy Shocks' and estimate 'Regime Cohesion' and 'Kinetic Retaliation' based on today's data.")
        self.agent.act(until_done=True)

        # 4. Structural Synthesis thought
        self.agent.think("I have the US-Iran geopolitical wire. I will now synthesize the **US-IRAN TACTICAL DESK BRIEFING**.")
        self.agent.act(until_done=True)

        logger.info("Synthesizing Middle East War Wire with Cross-Verification...")
        self.agent.think("ACTION REQUIRED: You must now produce the **'US-IRAN ESCALATION INTELLIGENCE: MARCH 2026'** report.\n\n"
                         "### MIDDLE EAST DESK PROTOCOL ###\n"
                         "1. GULF NAVAL METRICS: Report exact shipping disruptions or chokepoint blockades in the Strait of Hormuz.\n"
                         "2. KINETIC STRIKES: Detail drone, missile, or air strikes by US, Israel, or Iran/Proxies.\n"
                         "3. ENERGY SHOCK: Provide explicit figures on oil price spikes, global market responses, and supply chain fractures.\n"
                         "4. REGIME COHESION: Output explicit stability metrics on Tehran's leadership and domestic tension.\n"
                         "5. ESCALATION POTENTIAL: Map the immediate next rungs on the escalation ladder based on recent actions.\n"
                         "6. SOURCE DIVERSITY: Cross-verify events and explicitly flag state media reports as 'Unverified Narrative' if they contradict OSINT.\n"
                         "7. TRAILING CONTEXT: Ensure the output uses the 'This follows...' logic to maintain a persistent timeline.\n"
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
                    if len(content) > 800 and ("IRAN" in content.upper() or "GULF" in content.upper()):
                        report = content
                        break
            if report:
                break
            self.agent.think("FAILURE: Too vague. I need the raw geopolitical pulse for the US-Iran war. "
                             "Mention specific strikes, oil metrics, regime stability, and escalation potential. "
                             "I am paying for high-fidelity tactical intelligence.")
        
        return report

    def commit(self, report):
        # Get costs
        costs = cost_manager.total_cost
        summary = cost_manager.get_summary()
        
        logger.info(f"Session Cost estimate: ${costs:.4f}")
        logger.info(f"Usage Summary: {summary['total_input_tokens']} in, {summary['total_output_tokens']} out")

        if not report:
            logger.error("No report generated. Skipping commit.")
            if costs > 0:
                cost_manager.save_run_to_history("US-Iran War Update (FAILED)")
            return
            
        logger.info(f"Committing briefing to {self.output_file}...")
        
        header = f"### US-IRAN ESCALATION INTELLIGENCE: {datetime.date.today().isoformat()} ###\n"
        header += "SOURCE: THE US-IRAN WAR DESK // ENERGY SHOCK AUDITOR\n"
        header += f"COMMISSIONING COST: ${costs:.4f}\n"
        header += "ESCALATION LEVEL: SEVERE\n\n"
        
        full_content = header + report
        
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        logger.info(f"Commit successful. Total Session Cost: ${costs:.4f}")
        cost_manager.save_run_to_history("US-Iran War Update")


if __name__ == "__main__":
    update = USIranWarUpdate()
    update.initialize()
    report = update.harvest_and_synthesize()
    update.commit(report)
