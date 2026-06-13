# FitFindr 🛍️

A multi-tool AI agent that helps users find secondhand clothing and style it with what they already own. Built with Python, Groq (llama-3.3-70b-versatile), and Gradio.

---

## How to Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your Groq API key to a `.env` file:
GROQ_API_KEY=your_key_here
Then run:
```bash
python3 app.py
```

Open the URL shown in your terminal (usually http://localhost:7860).

---

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) → list[dict]`
Searches the mock listings dataset for secondhand items matching the user's description. Filters by size and price if provided, then scores each remaining item by keyword overlap with the description. Returns a ranked list sorted by relevance score, or an empty list if nothing matches — never raises an exception.

### `suggest_outfit(new_item: dict, wardrobe: dict) → str`
Given a thrifted item and the user's wardrobe, calls the Groq LLM to suggest 1–2 complete outfit combinations using specific pieces from the wardrobe. If the wardrobe is empty, falls back to general styling advice for the item rather than crashing.

### `create_fit_card(outfit: str, new_item: dict) → str`
Generates a short, casual Instagram-style caption for the thrifted outfit. Uses LLM temperature 1.0 so the output varies each time. Guards against an empty outfit string — returns a descriptive error message instead of raising an exception.

### `compare_price(item: dict) → str`
Compares a listing's price to similar items in the database with the same 
category and overlapping style tags. Returns a plain-English price assessment 
— great deal, fair price, or on the higher end — with the average comparable 
price and number of listings compared.

### Style Profile Memory
After each successful interaction, FitFindr saves the user's wardrobe 
and last query to `style_memory.json`. On the next session, the app 
displays what was saved from the previous session. The memory file is 
stored locally and persists between app restarts.
---

## Planning Loop

The agent runs a linear planning loop with conditional branching at each step:

1. **Parse** — the user's natural language query is sent to the LLM, which extracts a structured `description`, `size`, and `max_price`
2. **Search** — `search_listings()` is called with the parsed parameters. If no results are found, the agent sets an error message and returns early — it never calls the remaining tools with empty input
3. **Select** — the top result becomes `selected_item` and is stored in the session
4. **Suggest** — `suggest_outfit()` is called with the selected item and the user's wardrobe
5. **Generate** — `create_fit_card()` is called with the outfit suggestion and selected item
6. **Return** — the completed session dict is returned to `app.py` which renders the three output panels

The loop does not call all tools unconditionally. It stops and returns an informative error at any step where a tool fails or returns nothing useful.

---

## State Management

All state is stored in a single session dict initialized at the start of each interaction:

```python
{
    "query": str,              # original user query
    "parsed": dict,            # extracted description, size, max_price
    "search_results": list,    # all matching listings
    "selected_item": dict,     # top result — passed into suggest_outfit
    "wardrobe": dict,          # user's wardrobe — passed into suggest_outfit
    "outfit_suggestion": str,  # returned by suggest_outfit — passed into create_fit_card
    "fit_card": str,           # returned by create_fit_card
    "error": str | None,       # set if any step fails
}
```

Each tool's output is written to the session before the next tool is called. No values are re-entered or hardcoded between steps — the item found by `search_listings` flows directly into `suggest_outfit` without the user having to re-describe it.

---

## Error Handling

| Tool | Failure mode | Agent response | Example |
|------|-------------|----------------|---------|
| `search_listings` | No results match the query | Sets `session["error"]` with a message listing the filters applied and suggesting the user broaden their search. Returns early — does not call remaining tools. | Query: "designer ballgown size XXS under $5" → "No listings found matching 'designer ballgown' in size XXS under $5. Try broadening your search..." |
| `suggest_outfit` | Wardrobe is empty | Falls back to general styling advice from the LLM instead of specific combinations. Never raises an exception. | Empty wardrobe → "What a fun find. To create a cohesive look with the Y2K Baby Tee, I'd suggest pairing it with high-waisted jeans or a flowy skirt..." |
| `create_fit_card` | Outfit input is empty | Returns a descriptive error string without raising an exception. | Empty outfit string → "Unable to generate a fit card — no outfit suggestion was provided." |
### Retry Logic
If `search_listings` returns no results and a size filter was applied, 
the agent automatically retries without the size constraint and informs 
the user what was adjusted. If the retry also returns no results, the 
agent sets an error and stops.
---

## Spec Reflection

The planning loop ended up simpler than I expected, a linear sequence with early returns at each failure point was cleaner than a branching decision tree. The most important design decision was using the LLM to parse the user's query (`_parse_query()`) rather than writing regex. This handles natural language like "something under thirty bucks in a medium" correctly, which regex would struggle with.

One divergence from the original spec: the empty wardrobe case for 
suggest_outfit was originally treated as a pure failure mode, but in implementation it became a genuine feature, the agent gives general styling advice to new users who haven't entered their wardrobe yet, rather than stopping entirely. This was a better outcome than the spec anticipated, so the spec was updated to reflect it.

The empty wardrobe case for `suggest_outfit` was more useful than expected — rather than being a pure failure mode, it became a genuine feature where the agent gives general styling advice to new users who haven't entered their wardrobe yet.

---

## AI Usage

**Instance 1 — Implementing `search_listings()`:**
I gave Claude the Tool 1 spec from `planning.md` (inputs, return value, failure mode) along with the field names from `listings.json`. I asked it to implement the function using `load_listings()` from the data loader. Claude generated the keyword scoring logic correctly. I reviewed it against my spec and verified the price and size filtering matched what I described before running it.

**Instance 2 — Implementing `run_agent()`:**
I gave Claude the Architecture diagram and the Planning Loop + State Management sections from `planning.md`. Claude generated the full planning loop including the `_parse_query()` helper that uses the LLM to extract structured parameters from natural language. I reviewed it to confirm it branched on the `search_listings` result (not calling all tools unconditionally) and stored values in the session dict at each step before accepting it.

---

## Stretch Features

### Retry Logic
If `search_listings` returns no results and a size filter was applied, the agent automatically retries without the size constraint and informs the user what was adjusted. If the retry also returns no results, the agent sets an error and stops.

### Price Comparison Tool
`compare_price(item: dict) → str` compares a listing's price to similar items in the database with the same category and overlapping style tags. Returns a plain-English price assessment — great deal, fair price, or on the higher end — with the average comparable price and number of listings compared. Shown in the listing panel below the item description.

### Style Profile Memory
After each successful interaction, FitFindr saves the user's wardrobe and last query to `style_memory.json`. On the next session, the app displays what was saved from the previous session without the user re-entering anything. The memory file is stored locally and persists between app restarts.