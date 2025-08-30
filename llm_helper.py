import os
from typing import Dict, Optional, List
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# -----------------------------
# HARDCODED GEMINI API KEY
# -----------------------------
_API_KEY = "AIzaSyDwPbSW9qXfXyVbB-rR3pVZxDwn_PRsUVA"  # 🔴 Replace with your Gemini key

if _API_KEY and genai:
    genai.configure(api_key=_API_KEY)

_MODEL_NAME = "gemini-1.5-flash"

OPENERS: List[str] = [
    "Comic fact-check time! 🕵️‍♂️✨",
    "Myth-busting cape on! 🦸‍♀️",
    "Let’s unpack this like a snack pack 🍿",
    "Science squad, assemble! 🧪"
]
CLOSERS: List[str] = [
    "Case closed. 🧠🔒",
    "Bookmark this for your next debate. 🔖",
    "Tell a friend and save a cow. 🐄💚",
    "Screenshottable truth unlocked. 📸✅"
]

def _style_prompt(
    query: str,
    myth: Optional[Dict] = None,
    tone: str = "comic",
    animal_nutrition: Optional[dict] = None,
    plant_nutrition: Optional[dict] = None
) -> str:
    opener = OPENERS[hash(query) % len(OPENERS)]
    closer = CLOSERS[hash(query[::-1]) % len(CLOSERS)]

    style = {
        "comic": "Playful, Gen Z, punchy sentences, 3–5 lines max. Use a couple of emojis. Be factual but encourage plant-based and animal-friendly choices.",
        "snarky": "Witty, lightly sarcastic, 3–5 lines. Highlight animal welfare and ethical considerations, encouraging plant alternatives.",
        "warm": "Empathetic, encouraging, friendly. 3–5 lines. Promote plant-based diets and animal-conscious choices warmly."
    }.get(tone, "Playful, clear, short.")

    if myth:
        base = f"""Myth: {myth.get('myth')}
Truth: {myth.get('truth')}
Advice: {myth.get('advice', '')}
"""
    else:
        base = "No database match; answer from general knowledge but stay cautious and concise.\n"

    nutrition_info = ""
    if animal_nutrition and plant_nutrition:
        nutrition_info = f"""
Nutrition Comparison:
- Animal Product: {animal_nutrition['food']} — {animal_nutrition['Protein_g']} g protein, {animal_nutrition['Calories']} calories
- Plant Alternative: {plant_nutrition['food']} — {plant_nutrition['Protein_g']} g protein, {plant_nutrition['Calories']} calories

Please suggest the approximate quantity of the plant alternative needed to match the protein content of the animal product.
"""

    prompt = f"""
System: You are a myth-busting assistant for animal/food topics serving the India Animal Fund mission. Be factual, but prioritize promoting plant-based alternatives.
Style: {style}

{opener}

User asked: {query}

Context:
{base}
{nutrition_info}

Rules:
- Start with a verdict like “Verdict: Myth”, “Fact”, or “Mixed”.
- Give a short explanation (2–4 lines) with facts comparing animal product and plant alternative.
- Clearly state any nutritional strengths of animal products but highlight the cons (environmental impact, animal welfare, health).
- Encourage using plant-based alternatives highlighting their benefits.
- Provide up to 2 credible sources with titles and URLs.
- Format sources as markdown links [Title](URL).
- Suggest the plant alternative serving size needed to match the animal product's protein.
- End with: {closer}
"""
    return prompt.strip()

def generate_comic_reply(
    query: str,
    myth: Optional[Dict] = None,
    tone: str = "comic",
    animal_nutrition: Optional[dict] = None,
    plant_nutrition: Optional[dict] = None
) -> str:
    if not (_API_KEY and genai):
        # fallback
        if myth:
            return f"Verdict: Myth.\n{myth.get('truth')}\nAdvice: {myth.get('advice')}\n(LLM disabled: showing DB truth.)"
        return "LLM not configured and no DB match. Add GEMINI_API_KEY to enable comic replies."

    prompt = _style_prompt(query, myth, tone, animal_nutrition, plant_nutrition)

    try:
        model = genai.GenerativeModel(_MODEL_NAME)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        if text:
            return text
        # fallback to DB if empty
        if myth:
            return f"Verdict: Myth.\n{myth.get('truth')}\nAdvice: {myth.get('advice')}"
        return "No reply generated."
    except Exception as e:
        if myth:
            return f"Verdict: Myth.\n{myth.get('truth')}\nAdvice: {myth.get('advice')}\n(LLM error: {e})"
        return f"(LLM error: {e})"
