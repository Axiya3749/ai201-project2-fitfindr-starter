"""
app.py
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
from memory import load_style_profile, clear_style_profile


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    # Guard against empty query
    if not user_query or not user_query.strip():
        return "Please enter a search query.", "", ""

    # Select wardrobe
    if wardrobe_choice == "Example wardrobe":
        wardrobe = get_example_wardrobe()
    else:
        wardrobe = get_empty_wardrobe()

    # Run the agent
    session = run_agent(query=user_query, wardrobe=wardrobe)

    # Handle error
    if session["error"]:
        return session["error"], "", ""

    # Format the listing
    item = session["selected_item"]
    retry_note = session.get("retry_note") or ""
    price_assessment = session.get("price_assessment") or ""
    listing_text = (
        f"{retry_note + chr(10) + chr(10) if retry_note else ''}"
        f"{item['title']}\n"
        f"${item['price']} — {item['platform']}\n"
        f"Size: {item['size']} | Condition: {item['condition']}\n"
        f"Brand: {item.get('brand') or 'Unknown'}\n\n"
        f"{item['description']}\n\n"
        f"💰 Price check: {price_assessment}"
    )

    return listing_text, session["outfit_suggestion"], session["fit_card"]


# ── memory helpers ────────────────────────────────────────────────────────────

def _get_memory_status() -> str:
    memory = load_style_profile()
    if memory:
        return f"💾 Style memory loaded from last session (last searched: \"{memory['last_query']}\")"
    return "No saved style memory yet — one will be created after your first search."


def handle_query_with_memory(user_query: str, wardrobe_choice: str):
    listing, outfit, fitcard = handle_query(user_query, wardrobe_choice)
    return listing, outfit, fitcard, _get_memory_status()


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",
]


def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        memory_output = gr.Markdown(value=_get_memory_status())

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query_with_memory,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output, memory_output],
        )
        query_input.submit(
            fn=handle_query_with_memory,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output, memory_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()