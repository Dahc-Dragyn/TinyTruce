import sys
import os
import tinytroupe
from tinytroupe.cost_manager import cost_manager

print(f"tinytroupe file: {tinytroupe.__file__}")
print(f"cost_manager id: {id(cost_manager)}")
print(f"sys.path: {sys.path}")

import tinytroupe.openai_utils
from tinytroupe.llm_engine import cost_manager as engine_cost_manager

print(f"engine_cost_manager id: {id(engine_cost_manager)}")
print(f"Are they the same? {cost_manager is engine_cost_manager}")
