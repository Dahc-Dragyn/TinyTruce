from tinytroupe.cost_manager import cost_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_cost")

logger.info(f"Initial cost: {cost_manager.total_cost}")
cost_manager.add_usage("gemini-2.5-flash-lite", 1000, 500)
logger.info(f"Updated cost: {cost_manager.total_cost}")
print(f"TOTAL_COST={cost_manager.total_cost}")
