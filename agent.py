"""
agent.py
"""

import os
import re
import json
from dotenv import load_dotenv
from groq import Groq
from tools import search_listings, suggest_outfit, create_fit_card, compare_price
from memory import save_style_profile

load_dotenv()


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")
    return Groq(api_key=api_key)


def _parse_query(query: str) -> dict:
    """Use the LLM to extract description, size, and max_price from the query."""
    client = _get_groq_client()
    prompt = (
        f"Extract search parameters from this thrift shopping query:\n\"{query}\"\n\n"
        f"Return ONLY a JSON object with these fields:\n"
        f"  description: the item being searched for (string)\n"
        f"  size: the size if mentioned, or null\n"
        f"  max_price: the maximum price as a number if mentioned, or null\n\n"
        f"Example: {{\"description\": \"vintage graphic tee\", \"size\": \"M\", \"max_price\": 30}}\n"
        f"Return only the JSON, no other text."
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content.strip()
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
        "retry_note": None,
        "price_assessment": None,
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)

    # Step 1: Parse the query
    try:
        session["parsed"] = _parse_query(query)
    except Exception as e:
        session["error"] = f"Couldn't understand your query: {e}"
        # Save style profile for next session
        save_style_profile(
            wardrobe=session["wardrobe"],
            last_query=session["query"],
    )
        return session

    parsed = session["parsed"]

    # Step 2: Search listings
    results = search_listings(
        description=parsed.get("description", query),
        size=parsed.get("size"),
        max_price=parsed.get("max_price"),
    )
    session["search_results"] = results

    # If no results, try retry logic
    if not results:
        if parsed.get("size"):
            # Retry without size filter
            results = search_listings(
                description=parsed.get("description", query),
                size=None,
                max_price=parsed.get("max_price"),
            )
            if results:
                session["search_results"] = results
                session["retry_note"] = (
                    f"⚠️ No results found in size {parsed['size']}, "
                    f"so I removed the size filter and found these instead."
                )
            else:
                session["error"] = (
                    f"No listings found matching '{parsed.get('description', query)}'"
                    + (f" in size {parsed['size']}" if parsed.get("size") else "")
                    + (f" under ${parsed['max_price']}" if parsed.get("max_price") else "")
                    + ". Try broadening your search — remove the size or price filter, or use different keywords."
                )
                return session
        else:
            session["error"] = (
                f"No listings found matching '{parsed.get('description', query)}'"
                + (f" under ${parsed['max_price']}" if parsed.get("max_price") else "")
                + ". Try broadening your search — use different keywords or remove the price filter."
            )
            return session

    # Step 3: Select top result
    session["selected_item"] = results[0]
    # Step 3.5: Compare price
    session["price_assessment"] = compare_price(session["selected_item"])
    # Step 4: Suggest outfit
    try:
        session["outfit_suggestion"] = suggest_outfit(
            new_item=session["selected_item"],
            wardrobe=session["wardrobe"],
        )
    except Exception as e:
        session["error"] = f"Couldn't generate outfit suggestion: {e}"
        return session

    # Step 5: Create fit card
    try:
        session["fit_card"] = create_fit_card(
            outfit=session["outfit_suggestion"],
            new_item=session["selected_item"],
        )
    except Exception as e:
        session["error"] = f"Couldn't generate fit card: {e}"
        return session

    return session


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")