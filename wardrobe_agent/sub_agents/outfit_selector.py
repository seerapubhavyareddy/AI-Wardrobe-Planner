from google.adk.agents import LlmAgent
from wardrobe_agent.tools import get_wardrobe_context, check_and_save_outfit
from wardrobe_agent.prompts import OUTFIT_SELECTOR_PROMPT

outfit_selector_agent = LlmAgent(
    name="outfit_selector",
    model="gemini-2.5-flash",
    instruction=OUTFIT_SELECTOR_PROMPT,
    tools=[get_wardrobe_context, check_and_save_outfit],
    description=(
        "Selects a clothing combination (top+bottom or dress) from the wardrobe "
        "based on occasion, style, and weather. Avoids previously suggested outfits."
    ),
)
