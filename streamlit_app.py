import os
import json
import base64
import re
import streamlit as st
from typing import Dict, Optional, List
import markdown

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# -----------------------------
# HARDCODED GEMINI API KEY
# -----------------------------
_API_KEY = "AIzaSyDwPbSW9qXfXyVbB-rR3pVZxDwn_PRsUVA"  # Replace with your Gemini key

if _API_KEY and genai:
    genai.configure(api_key=_API_KEY)

_MODEL_NAME = "gemini-1.5-flash"

OPENERS: List[str] = [
    "Comic fact-check time! 🕵️‍♂️✨",
    "Myth-busting cape on! 🦸‍♀️",
    "Let’s unpack this like a snack pack 🍿",
    "Science squad, assemble! 🧪"
]
# Removed old comic closing lines
CLOSERS: List[str] = [
    "Case closed. 🧠🔒",
    "Bookmark this for your next debate. 🔖",
    "Tell a friend and save a cow. 🐄💚"
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
        "comic": (
            "Playful, Gen Z, punchy sentences, 5 points max in bullet form. Use clear bullet points. "
            "Add quantity & quality info where applicable. Use a couple of emojis. "
            "Be factual but encourage plant-based and animal-friendly choices."
        ),
        "snarky": (
            "Witty, lightly sarcastic, 5 bullet points max. "
            "Highlight animal welfare and ethical considerations. Encourage plant alternatives."
        ),
        "warm": (
            "Empathetic, encouraging, friendly, 5 concise bullet points. "
            "Promote plant-based diets and animal-conscious choices warmly."
        )
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
- Animal product: {animal_nutrition['food']} — {animal_nutrition['Protein_g']} g protein, {animal_nutrition['Calories']} calories
- Plant alternative: {plant_nutrition['food']} — {plant_nutrition['Protein_g']} g protein, {plant_nutrition['Calories']} calories

Please provide approximate quantity of the plant alternative to match protein content of animal product.
"""

    prompt = f"""
System: You are a myth-busting assistant working for India Animal Fund. Be factual but prioritize promoting plant-based alternatives.
Style: {style}

{opener}

User asked: {query}

Context:
{base}
{nutrition_info}

Rules:
- Start with a short verdict like “Verdict: Myth”, “Fact”, or “Mixed”.
- Give a detailed answer in **5 clear bullet points** with nutritional quantities, quality comparisons, and environmental/ethical facts.
- Encourage plant-based alternatives highlighting benefits.
- Provide up to 2 credible sources in markdown links.
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


# -------- Streamlit UI --------

st.set_page_config(
    page_title="🐾 India Animal Fund - Ask me anything",
    page_icon="🌈",
    layout="wide"
)

# Rainbow gradient for title text
st.markdown(
    """
    <h1 style="
        background: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 3.5rem;
        margin-bottom: 0.3rem;
    ">India Animal Fund - Ask me anything</h1>
    """,
    unsafe_allow_html=True,
)

st.subheader("Ask me about an animal or food myth:")

user_input = st.text_input("Type your question here:")

tone = st.radio("Choose tone:", ["comic", "snarky", "warm"])


def clean_trailing_html(text):
    # Remove trailing closing div or other tags, prevent raw '</div>' text
    return re.sub(r'</?div[^>]*>\s*$', '', text.strip(), flags=re.IGNORECASE)


def format_answer_as_points(raw_text):
    # Clean trailing html tags first
    raw_text = clean_trailing_html(raw_text)

    # Remove last closer line by splitting on known closers
    for closer in CLOSERS:
        if closer in raw_text:
            raw_text = raw_text.split(closer)[0].strip()
            break

    # Convert Markdown to HTML
    html_answer = markdown.markdown(raw_text)

    # Append veganism quote in HTML
    html_answer += """
    <p style='font-style: italic; margin-top: 15px; color:#F5B041; font-weight: bold;'>
        🌱 “Be the change you wish to see in the world.” – Mahatma Gandhi
    </p>
    """
    return html_answer


if st.button("Check Myth"):
    if user_input:
        # Load myth data from myths.json
        try:
            with open("myths.json", "r") as f:
                myths_data = json.load(f)
                myths = myths_data["myths"]
        except Exception:
            myths = []

        # Find matching myth entry (case-insensitive substring search)
        myth_entry = next((m for m in myths if user_input.lower() in m["myth"].lower()), None)

        answer = generate_comic_reply(user_input, myth_entry, tone)

        formatted_answer = format_answer_as_points(answer)

        st.markdown(
            f"""
            <div style="
                background-color:#000000;
                color:#FFFFFF;
                padding:20px;
                border-radius:10px;
                font-size:16px;
                line-height:1.5em;
                white-space: normal;
            ">
                {formatted_answer}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Show advice box if available
        if myth_entry and "advice" in myth_entry:
            st.markdown(
                f"""
                <div style="
                    background-color:#1B2631;
                    color:#F5B041;
                    padding:12px;
                    border-radius:8px;
                    font-weight:bold;
                    font-size:15px;
                    margin-top:10px;
                ">
                    🐾 Advice: {myth_entry['advice']}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Show first two credible sources if available
        if myth_entry and "citations" in myth_entry:
            citations = myth_entry["citations"][:2]
            citation_text = " | ".join([f"[{c['title']}]({c['url']})" for c in citations])
            st.markdown(
                f"""
                <div style='color:#F5B041; font-size:14px; margin-top:10px;'>
                    Sources: {citation_text}
                </div>
                """,
                unsafe_allow_html=True,
            )
