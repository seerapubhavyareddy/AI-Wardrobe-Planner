from google.adk.agents import SequentialAgent
from wardrobe_agent.sub_agents.outfit_loop import outfit_loop
from wardrobe_agent.sub_agents.styling_agent import styling_agent

# SequentialAgent runs sub_agents in strict order:
# 1. outfit_loop  → finds a fresh clothing combination (uses LoopAgent internally)
# 2. styling_agent → adds accessories based on the chosen outfit + context
outfit_pipeline = SequentialAgent(
    name="outfit_pipeline",
    sub_agents=[outfit_loop, styling_agent],
    description=(
        "The main outfit generation pipeline. Runs outfit selection (with no-repeat loop) "
        "followed by accessory styling in sequence."
    ),
)
