import json
import logging
import os
import datetime

logger = logging.getLogger("tinytroupe")

class CostManager:
    """
    Manages and calculates simulation costs based on token usage.
    """
    
    # Default pricing as of Feb 25, 2026 (per 1M tokens)
    # This can be overridden or loaded from Gemini_Pricing.md
    DEFAULT_PRICING = {
        "gemini-2.5-flash-lite-preview-09-2025": {"input": 0.10, "output": 0.40, "cached": 0.025},
        "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40, "cached": 0.025},
        "gemini-2.0-flash-lite-001": {"input": 0.075, "output": 0.30, "cached": 0.01875}
    }
    
    def __init__(self, pricing_path=None):
        if pricing_path is None:
            # Default location in DOCUMENTS
            pricing_path = os.path.join(os.getcwd(), "DOCUMENTS", "Gemini_Pricing.json")
            
        self.pricing = self.DEFAULT_PRICING.copy()
        self.load_pricing_json(pricing_path)
        
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.total_cost = 0.0
        self.usage_history = [] 

    def load_pricing_json(self, path):
        """Loads pricing from a JSON file if available."""
        if not os.path.exists(path):
            logger.debug(f"Pricing JSON not found at {path}, using defaults.")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                new_pricing = data.get("models", {})
                # Merge with defaults
                for model, rates in new_pricing.items():
                    self.pricing[model] = rates
            logger.info(f"Loaded dynamic pricing from {path}")
        except Exception as e:
            logger.warning(f"Failed to load pricing JSON: {e}")
            
    def save_run_to_history(self, scenario_name):
        """Appends a compact summary to the JSONL log and a readable row to the Markdown ledger."""
        doc_dir = os.path.join(os.getcwd(), "DOCUMENTS")
        jsonl_path = os.path.join(doc_dir, "tinytruce_billing.jsonl")
        ledger_path = os.path.join(doc_dir, "tinytruce_billing_ledger.md")
        
        summary = self.get_summary()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Compact JSONL (Machine readable, but lean)
        compact_entry = {
            "timestamp": timestamp,
            "scenario": scenario_name,
            "total_input": summary["total_input_tokens"],
            "total_output": summary["total_output_tokens"],
            "total_cached": summary["total_cached_tokens"],
            "total_cost": summary["total_cost"]
        }
        
        try:
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(compact_entry) + "\n")
            logger.info(f"Compact billing saved: {jsonl_path}")
        except Exception as e:
            logger.warning(f"Failed to save to JSONL billing log: {e}")

        # 2. Markdown Ledger (Human readable)
        header = "| Timestamp | Scenario | Input | Output | Cached | Cost ($) |\n"
        separator = "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        row = f"| {timestamp} | {scenario_name} | {summary['total_input_tokens']:,} | {summary['total_output_tokens']:,} | {summary['total_cached_tokens']:,} | **${summary['total_cost']:.4f}** |\n"
        
        try:
            file_exists = os.path.exists(ledger_path)
            with open(ledger_path, "a", encoding="utf-8") as f:
                if not file_exists:
                    f.write("# TinyTruce Billing Ledger\n\n")
                    f.write(header)
                    f.write(separator)
                f.write(row)
            logger.info(f"Billing ledger updated: {ledger_path}")
        except Exception as e:
            logger.warning(f"Failed to update billing ledger: {e}")

    def add_usage(self, model_name, input_tokens, output_tokens, cached_tokens=0, agent_name=None, turn=None):
        """
        Record usage and calculate cost.
        """
        # Normalize model name for lookup (strip 'models/' prefix)
        lookup_name = model_name
        if model_name.startswith("models/"):
            lookup_name = model_name[7:]
            
        rates = self.pricing.get(lookup_name)
        if not rates:
            # Try to find a partial match (e.g. if lookup is 'gemini-1.5-flash-001' but we have 'gemini-1.5-flash')
            for key in self.pricing:
                if key in lookup_name:
                    rates = self.pricing[key]
                    break
            
            if not rates:
                rates = self.pricing.get("gemini-2.5-flash-lite")
        
        # Costs in JSON are per 1M tokens
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        
        # If cached cost isn't explicit, assume 25% of input cost per industry standard
        cached_rate = rates.get("cached", rates["input"] * 0.25)
        cached_cost = (cached_tokens / 1_000_000) * cached_rate
        
        call_cost = input_cost + output_cost + cached_cost
        
        usage_entry = {
            "model": model_name,
            "agent": agent_name,
            "turn": turn,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "cost": call_cost
        }
        
        self.usage_history.append(usage_entry)
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cached_tokens += cached_tokens
        self.total_cost += call_cost
        
        return call_cost

    def get_summary(self):
        """
        Returns a summary dictionary of the usage.
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cached_tokens": self.total_cached_tokens,
            "total_cost": round(self.total_cost, 6),
            "usage_history": self.usage_history
        }

    def reset(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.total_cost = 0.0
        self.usage_history = []

# Global instance for easy access across the project
cost_manager = CostManager()
