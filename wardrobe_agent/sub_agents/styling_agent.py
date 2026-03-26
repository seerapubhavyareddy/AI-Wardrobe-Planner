from google.adk.agents import LlmAgent
from wardrobe_agent.tools import get_wardrobe_context
from wardrobe_agent.prompts import STYLING_PROMPT

styling_agent = LlmAgent(
    name="styling_agent",
    model="gemini-2.5-flash",
    instruction=STYLING_PROMPT,
    tools=[get_wardrobe_context],
    description=(
        "Completes the outfit by selecting accessories: earrings, footwear, and handbag "
        "based on occasion, style mood, and weather conditions."
    ),
)
