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
logger = logging.getLogger("ukraine_tactical_update")

# Root path for all relative project assets
ROOT = Path(__file__).parent.parent.absolute()

class UkraineTacticalUpdate:
    def __init__(self, output_file=None):
        if output_file is None:
            # Default location in project root
            self.output_file = ROOT / "data" / "facts" / "ukraine-frontline-intelligence.2026.txt"
        else:
            self.output_file = Path(output_file).absolute()
            
        self.agent = None
        self.situation_room = None
        
    def initialize(self):
        logger.info(f"Initializing Ukraine Tactical Desk (Running from: {ROOT})...")
        # Ensure we're in the project root to fix config.ini and path lookup issues
        os.chdir(ROOT)
        
        # Force Native Gemini engine to bypass OpenAI adapter issues
        os.environ["TINYTRUCE_FORCE_NATIVE_LLM"] = "true"
        
        # Reset costs at start
        cost_manager.reset()
        
        agent_path = ROOT / "personas" / "agents" / "ukraine_tactical_desk.agent.json"
        
        if not agent_path.exists():
            raise FileNotFoundError(f"[FATAL]: Could not find agent at {agent_path}")
            
        self.agent = TinyPerson.load_specification(str(agent_path))
        
        # Add Situation Room faculty
        self.situation_room = SituationRoomFaculty()
        self.agent.add_mental_faculty(self.situation_room)
        
    def harvest_and_synthesize(self):
        logger.info("Harvesting Ukraine theater news from Situation Room...")
        self.agent.show_thoughts = True # Force visibility during update
        
        # 1. Get High-Severity Alerts for Ukraine (MANDATORY START)
        logger.info("Requesting Ukraine High-Severity Alerts...")
        self.agent.think("System Command: Execute GET_ALERTS. Prioritize items concerning Ukraine, Russia, and direct spillover effects.")
        # 2. Ukraine Frontline Direct Feed Harvest
        feeds = {
            "Google News": "https://news.google.com/rss/search?q=Ukraine+frontline+war&hl=en-US&gl=US&ceid=US:en",
            "Ukraine Crisis Media Center": "https://uacrisis.org/en/feed",
            "Kyiv Post": "https://www.kyivpost.com/feed",
            "William Spaniel (OSINT)": "https://www.youtube.com/feeds/videos.xml?playlist_id=PLKI1h_nAkaQrxEzfdylXh33gweZZEqrdV",
            "Interfax-Ukraine": "https://en.interfax.com.ua/news/last.rss",
            "Kyiv Independent": "https://kyivindependent.com/news-archive/rss/",
            "ISW": "https://www.understandingwar.org/rss.xml"
        }
        
        feed_content = []
        import requests
        import xml.etree.ElementTree as ET
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

        for name, rss_url in feeds.items():
            logger.info(f"Fetching {name} RSS feed...")
            try:
                response = requests.get(rss_url, headers=headers, timeout=10)
                response.raise_for_status()
                root = ET.fromstring(response.content)
                
                feed_items = []
                # Get top 5 from each to avoid massive context
                for item in root.findall('.//item')[:5] if root.findall('.//item') else root.findall('.//{http://www.w3.org/2005/Atom}entry')[:5]:
                    title_elem = item.find('title') if item.find('title') is not None else item.find('{http://www.w3.org/2005/Atom}title')
                    title = title_elem.text if title_elem is not None else 'No Title'
                    feed_items.append(f"- {title}")
                    
                if feed_items:
                    feed_content.append(f"### {name} ###\n" + "\n".join(feed_items))
                    
            except Exception as e:
                logger.warning(f"Failed to fetch {name} feed: {e}")

        if feed_content:
            all_feeds_text = "\n\n".join(feed_content)
            self.agent.think(f"### [UKRAINE MULTI-SOURCE OSINT HARVEST] ###\n\n{all_feeds_text}\n\n"
                             "If you find that data is scarce or dominated by other theaters (like Iran), "
                             "you MUST document this 'Information Blackout' or 'Resource Diversion' as a tactical signal for Ukraine.")
            self.agent.act(until_done=True)
            time.sleep(2)
        else:
            logger.error("All RSS feeds failed. Proceeding with generic search.")
            self.agent.think("### [SYSTEM ERROR] ###\nAll primary OSINT feeds failed. FALLBACK: Use SEARCH_NEWS to find specific March 2026 frontline sectors.")
            self.agent.act(until_done=True)

        # 3. Quantitative Metrics Logic
        logger.info("Executing Ukraine Quantitative Metrics Logic...")
        self.agent.think("I will now execute Attrition Modeling. I must calculate explicit 'Stability Drift' and estimate 'Depletion Horizons' for manpower, munitions, or territory based on today's data.")
        self.agent.act(until_done=True)

        # 4. Structural Synthesis thought
        self.agent.think("I have the Ukraine tactical wire. I will now synthesize the **UKRAINE TACTICAL DESK BRIEFING**.")
        self.agent.act(until_done=True)

        logger.info("Synthesizing Ukraine War Wire with Cross-Verification...")
        self.agent.think("ACTION REQUIRED: You must now produce the **'UKRAINE FRONTLINE INTELLIGENCE: MARCH 2026'** report.\n\n"
                         "### UKRAINE TACTICAL DESK PROTOCOL ###\n"
                         "1. FRONTLINE FIDELITY: Report exact Line of Contact changes and Key sectors (e.g., Pokrovsk, Kupiansk, Zaporizhia).\n"
                         "2. ATTRITION METRICS: Provide daily/weekly casualty estimates and equipment losses.\n"
                         "3. EXTERNAL FACTORS: Track aid news, POW swaps, and Russian redeployments.\n"
                         "4. STABILITY DRIFT: Output explicit depletion horizons (e.g., 'Manpower threshold: 180 days unchanged').\n"
                         "5. SPILLOVER EFFECTS: Highlight how global events (like the Middle East war) directly impact Ukraine's supplies or defenses.\n"
                         "6. SOURCE DIVERSITY: Cross-verify events and explicitly flag state media reports as 'Unverified Narrative' if they contradict OSINT.\n"
                         "7. TRAILING CONTEXT: Ensure the output uses the 'This follows...' logic to maintain a persistent timeline.\n"
                         "8. CITE everything from the wire.\n\n"
                         "YOUR VERY NEXT ACTION MUST BE 'TALK' CONTAINING THE FULL REPORT.")
        
        # Keep acting until a TALK action with significant content is produced
        max_attempts = 3
        report = ""
        best_effort_report = ""

        for attempt in range(max_attempts):
            actions = self.agent.act(until_done=True, return_actions=True)
            for action_content in actions:
                if action_content['action']['type'] == 'TALK':
                    content = action_content['action']['content']
                    
                    # Store the longest report as best effort
                    if len(content) > len(best_effort_report):
                        best_effort_report = content

                    # Lowered threshold: 400 chars. Ensure it's relevant.
                    if len(content) > 400 and "UKRAINE" in content.upper():
                        report = content
                        break
            if report:
                break
            
            self.agent.think(f"FAILURE: Report too brief ({len(best_effort_report)} chars). "
                             "I need more granular tactical intelligence or a detailed assessment of the 'Data Deficit'. "
                             "Attempt {attempt + 1}/{max_attempts}.")
        
        # Fallback: if we still don't have a report after max_attempts, take the best effort
        if not report and best_effort_report:
            logger.warning("Max attempts reached. Utilizing best-effort report.")
            report = best_effort_report
            
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
                cost_manager.save_run_to_history("Ukraine Tactical Update (FAILED)")
            return
            
        logger.info(f"Committing briefing to {self.output_file}...")
        
        header = f"### UKRAINE FRONTLINE INTELLIGENCE: {datetime.date.today().isoformat()} ###\n"
        header += "SOURCE: THE UKRAINE TACTICAL DESK // STABILITY AUDITOR\n"
        header += f"COMMISSIONING COST: ${costs:.4f}\n"
        header += "STABILITY LEVEL: VOLATILE\n\n"
        
        full_content = header + report
        
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        logger.info(f"Commit successful. Total Session Cost: ${costs:.4f}")
        cost_manager.save_run_to_history("Ukraine Tactical Update")


if __name__ == "__main__":
    update = UkraineTacticalUpdate()
    update.initialize()
    report = update.harvest_and_synthesize()
    update.commit(report)
