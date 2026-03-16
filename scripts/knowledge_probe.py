import os
import sys
import json
import argparse
import logging
from pathlib import Path

# 🚨 TINYTRUCE MANDATE: WE DO NOT USE OPENAI. WE ONLY USE GEMINI. 🚨
os.environ["TINYTRUCE_FORCE_NATIVE_LLM"] = "1"

# Add parent directory to path to import tinytruce_sim
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tinytruce_sim as sim
from tinytroupe.agent import TinyPerson
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

PROBE_QUESTIONS = [
    {
        "id": "bio_kids",
        "category": "Biographical",
        "question": "What are the names of all your children?",
        "intent": "Checking intrinsic biographical knowledge."
    },
    {
        "id": "bio_edu",
        "category": "Biographical",
        "question": "What high school did you graduate from?",
        "intent": "Checking specific intrinsic life details."
    },
    {
        "id": "geo_2026",
        "category": "Geopolitical (2026)",
        "question": "What is the 'SIRA Gold Peg' and how does it affect the petrodollar?",
        "intent": "Checking if forensic 2026 data is present or hallucinated."
    },
    {
        "id": "geo_jakarta",
        "category": "Geopolitical (2026)",
        "question": "What are the main stipulations of the 'Jakarta Maritime Accord'?",
        "intent": "Checking awareness of fictional treaty grounding."
    },
    {
        "id": "ling_wonk",
        "category": "Linguistic",
        "question": "Give me your thoughts on the 'multilateral framework for global infrastructure'.",
        "intent": "Checking for Anti-Wonk protocol compliance."
    }
]

def run_probe(agent_name, mode="naked", fragments=None):
    console.print(f"\n[bold cyan]Starting Probe: {agent_name} (Mode: {mode})[/bold cyan]")
    
    agent_dir = "personas/agents"
    frag_dir = "personas/fragments"
    agent_file = f"{agent_name}.agent.json" if not agent_name.endswith(".agent.json") else agent_name
    agent_path = os.path.join(agent_dir, agent_file)
    
    if not os.path.exists(agent_path):
        console.print(f"[bold red]Error: Agent file not found: {agent_path}[/bold red]")
        return None

    # Resolve original name for grounding lookup BEFORE loading (to avoid name override)
    orig_name = agent_name
    try:
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_data = json.load(f)
            orig_name = agent_data.get("persona", {}).get("name", agent_name)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not read agent name from JSON: {e}[/yellow]")

    # Load Agent
    new_name = f"{agent_name}_{mode}"
    person = TinyPerson.load_specification(agent_path, new_agent_name=new_name)
    person.show_thoughts = False

    # Load Fragments if provided
    if fragments:
        for f_name in fragments:
            f_path = os.path.join(frag_dir, f_name)
            if not f_name.endswith(".fragment.json"):
                f_path = os.path.join(frag_dir, f"{f_name}.fragment.json")
            
            if os.path.exists(f_path):
                person.import_fragment(f_path)
                console.print(f"[green]Imported fragment: {f_name}[/green]")
            else:
                console.print(f"[yellow]Warning: Fragment not found: {f_path}[/yellow]")

    if mode == "grounded":
        # Load Layer 0 Grounding
        grounding = sim.extract_agent_grounding(orig_name)
        if grounding:
            person.think(f"### LAYER 0: GROUNDING ###\n{grounding}")
        
        # Load Global/Daily Intel
        world_facts_path = "data/facts/world-facts.2026.txt"
        daily_intel_path = "data/facts/daily-intelligence.2026.txt"
        
        global_grounding = ""
        if os.path.exists(world_facts_path):
            with open(world_facts_path, "r", encoding="utf-8") as f:
                global_grounding = f.read()
        if os.path.exists(daily_intel_path):
            with open(daily_intel_path, "r", encoding="utf-8") as f:
                global_grounding += f"\n\n{f.read()}"
        
        if global_grounding:
            person.think(f"### GLOBAL INTELLIGENCE (2026) ###\n{global_grounding}")

    results = []
    
    for q in PROBE_QUESTIONS:
        console.print(f"[yellow]Probing {q['category']}...[/yellow]")
        person.listen(q['question'], source="User")
        
        # Act
        actions = person.act(return_actions=True)
        response = "NO RESPONSE"
        
        for action_item in actions:
            action = action_item.get('action')
            if action and action.get('type') == 'TALK':
                response = action.get('content')
                break
        
        results.append({
            "id": q["id"],
            "question": q["question"],
            "response": response
        })
        
        # Clear specific memory of this question to stay 'clean'
        person.episodic_memory.delete_episodes(0, 99)
        person.reset_prompt()

    return results

def main():
    parser = argparse.ArgumentParser(description="TinyTruce Knowledge Probe")
    parser.add_argument("--agent", default="donald_trump_unscripted", help="Agent name to probe")
    parser.add_argument("--mode", choices=["naked", "grounded", "both"], default="both", help="Probe mode")
    parser.add_argument("--fragments", nargs="+", default=None, help="Behavior fragments to load")
    args = parser.parse_args()

    agent_name = args.agent
    modes = [args.mode] if args.mode != "both" else ["naked", "grounded"]
    
    # Initialize cost tracking
    from tinytroupe.cost_manager import cost_manager
    cost_manager.reset()

    all_results = {}
    for mode in modes:
        all_results[mode] = run_probe(agent_name, mode, fragments=args.fragments)

    # Display Results
    table = Table(title=f"Knowledge Probe Results: {agent_name}")
    table.add_column("Category", style="cyan")
    table.add_column("Question", style="yellow")
    table.add_column("Naked Response", style="white")
    table.add_column("Grounded Response", style="green")

    for i, q in enumerate(PROBE_QUESTIONS):
        naked_list = all_results.get("naked", [])
        grounded_list = all_results.get("grounded", [])
        
        naked_resp = naked_list[i].get("response", "N/A") if i < len(naked_list) else "N/A"
        grounded_resp = grounded_list[i].get("response", "N/A") if i < len(grounded_list) else "N/A"
        
        # Truncate for table
        naked_short = (naked_resp[:150] + '...') if len(naked_resp) > 150 else naked_resp
        grounded_short = (grounded_resp[:150] + '...') if len(grounded_resp) > 150 else grounded_resp
        
        table.add_row(q["category"], q["question"], naked_short, grounded_short)

    console.print(table)
    
    # Save to file
    output_file = f"DOCUMENTS/runs/probe_{agent_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "agent": agent_name,
            "fragments": args.fragments,
            "questions": PROBE_QUESTIONS,
            "results": all_results
        }, f, indent=4)
    
    console.print(f"\n[bold green]Report saved to: {output_file}[/bold green]")

    # Logging cost to billing ledger
    try:
        cost_summary = cost_manager.get_summary()
        if cost_summary.get("total_input_tokens", 0) > 0:
            session_label = f"PROBE: {agent_name} (Mode: {args.mode})"
            if args.fragments:
                session_label += f" + Fragments: {','.join(args.fragments)}"
            cost_manager.save_run_to_history(session_label)
            console.print(f"[bold green]Costs logged to billing ledger: ${cost_summary['total_cost']:.6f}[/bold green]")
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to log costs: {e}[/yellow]")

if __name__ == "__main__":
    import datetime
    main()
