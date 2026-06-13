"""
tools.py
"""

import os
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()

    # Filter by price and size first
    filtered = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue
        filtered.append(item)

    # Score by keyword overlap with description
    keywords = description.lower().split()
    scored = []
    for item in filtered:
        searchable = " ".join([
            item["title"],
            item["description"],
            item["category"],
            " ".join(item["style_tags"]),
            " ".join(item["colors"]),
            item.get("brand") or "",
        ]).lower()
        score = sum(1 for kw in keywords if kw in searchable)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()
    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        prompt = (
            f"A user just found this secondhand item:\n"
            f"  Title: {new_item['title']}\n"
            f"  Description: {new_item['description']}\n"
            f"  Style tags: {', '.join(new_item['style_tags'])}\n"
            f"  Colors: {', '.join(new_item['colors'])}\n\n"
            f"They haven't told you what's in their wardrobe yet. "
            f"Suggest what kinds of pieces would pair well with this item "
            f"and describe the overall vibe of the outfit."
        )
    else:
        wardrobe_text = "\n".join(
            f"- {i['name']} ({i['category']}, {', '.join(i['colors'])}, tags: {', '.join(i['style_tags'])})"
            for i in wardrobe_items
        )
        prompt = (
            f"A user just found this secondhand item:\n"
            f"  Title: {new_item['title']}\n"
            f"  Description: {new_item['description']}\n"
            f"  Style tags: {', '.join(new_item['style_tags'])}\n"
            f"  Colors: {', '.join(new_item['colors'])}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_text}\n\n"
            f"Suggest 1-2 complete outfit combinations using the new item "
            f"and specific pieces from their wardrobe. Be specific about which "
            f"pieces to combine and why they work together."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Unable to generate a fit card — no outfit suggestion was provided."

    client = _get_groq_client()

    prompt = (
        f"Write a 2-4 sentence Instagram caption for this thrifted outfit.\n\n"
        f"The thrifted item: {new_item['title']} — ${new_item['price']} on {new_item['platform']}\n"
        f"The outfit: {outfit}\n\n"
        f"Make it sound casual and authentic, like a real OOTD post. "
        f"Mention the item name, price, and platform naturally (once each). "
        f"Capture the vibe in specific terms. Don't make it sound like a product description."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
    )
    return response.choices[0].message.content

# ── Tool 4: compare_price ─────────────────────────────────────────────────────

def compare_price(item: dict) -> str:
    """Compare an item's price to similar listings in the database."""
    listings = load_listings()

    # Find comparable items — same category, at least one matching style tag
    comparables = [
        l for l in listings
        if l["category"] == item["category"]
        and l["id"] != item["id"]
        and any(tag in l["style_tags"] for tag in item["style_tags"])
    ]

    if not comparables:
        return f"No comparable listings found to assess pricing for {item['title']}."

    prices = [l["price"] for l in comparables]
    avg = sum(prices) / len(prices)
    item_price = item["price"]

    if item_price < avg * 0.8:
        verdict = "a great deal"
    elif item_price < avg * 1.1:
        verdict = "a fair price"
    else:
        verdict = "on the higher end"

    return (
        f"{item['title']} is priced at ${item_price:.2f}. "
        f"Among {len(comparables)} comparable {item['category']} listings, "
        f"the average price is ${avg:.2f}. "
        f"This is {verdict}."
    )