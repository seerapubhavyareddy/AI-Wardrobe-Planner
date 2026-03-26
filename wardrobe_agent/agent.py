from google.adk.agents import LlmAgent
from wardrobe_agent.tools import get_weather, load_wardrobe
from wardrobe_agent.sub_agents import outfit_pipeline
from wardrobe_agent.prompts import ORCHESTRATOR_PROMPT

root_agent = LlmAgent(
    name="wardrobe_orchestrator",
    model="gemini-2.5-flash",
    instruction=ORCHESTRATOR_PROMPT,
    tools=[get_weather, load_wardrobe],
    sub_agents=[outfit_pipeline],
    description=(
        "Root orchestrator for the AI Wardrobe Planner. Collects user context "
        "(occasion, style, city), fetches weather, loads the wardrobe, and delegates "
        "to the outfit pipeline to generate a complete, styled outfit recommendation."
    ),
)
