from google.adk.agents import LoopAgent
from wardrobe_agent.sub_agents.outfit_selector import outfit_selector_agent

# LoopAgent runs the outfit_selector_agent repeatedly until it finds a
# fresh (non-repeated) outfit. The loop exits when check_and_save_outfit
# sets tool_context.actions.escalate = True (status: "accepted").
# max_iterations caps the loop in case the wardrobe runs low on options.
outfit_loop = LoopAgent(
    name="outfit_loop",
    sub_agents=[outfit_selector_agent],
    max_iterations=3,
)
