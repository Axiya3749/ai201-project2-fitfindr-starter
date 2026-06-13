# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

search_listings, suggest_outfit, create_fit_card

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for secondhand items matching the user's description, optionally filtering by size and maximum price. Returns a ranked list of matches sorted by keyword relevance. 

**Input parameters:**
- `description` (str): Keywords describing the item (e.g. "vintage graphic tee")
- `size` (str | None): Size string to filter by, or None to skip size filtering. Case-insensitive.
- `max_price` (float | None): Maximum price inclusive, or None to skip price filtering.

**What it returns:**
A list of matching listing dicts sorted by relevance score (highest first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns an empty list if nothing matches.

**What happens if it fails or returns nothing:**
The agent sets `session["error"]` to a helpful message telling the user what filters were applied and suggesting they broaden their search (remove size filter, raise price limit, or try different keywords). The agent returns early and does not call `suggest_outfit` with empty input.

---

### Tool 2: suggest_outfit

**What it does:**
Given a thrifted item and the user's wardrobe, calls the Groq LLM to suggest 1–2 complete outfit combinations. Handles the case where the wardrobe is empty by offering general styling advice instead.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A listing dict — the item the user is considering buying.
- `wardrobe` (dict): A wardrobe dict with an `items` key containing a list of wardrobe item dicts. May be empty.

**What it returns:**
A non-empty string with outfit suggestions. If the wardrobe is empty, returns general styling advice for the item instead of specific combinations.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, the tool falls back to general styling advice rather than raising an exception. If the LLM call fails, the agent catches the exception, sets `session["error"]`, and returns early without calling `create_fit_card`.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable Instagram-style caption for the thrifted outfit. Uses a higher LLM temperature (1.0) so the output sounds different each time.

**Input parameters:**
- `outfit` (str): The outfit suggestion string from `suggest_outfit()`.
- `new_item` (dict): The listing dict for the thrifted item.

**What it returns:**
A 2–4 sentence casual caption mentioning the item name, price, and platform naturally. Sounds like a real OOTD post, not a product description.

**What happens if it fails or returns nothing:**
If `outfit` is empty or whitespace-only, returns a descriptive error string without raising an exception. If the LLM call fails, the agent catches the exception and sets `session["error"]`.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
The agent runs a linear planning loop with conditional branching at each step:

1. Parse the user's query using the LLM to extract `description`, `size`, and `max_price`
2. Call `search_listings()` with the parsed parameters
3. If no results → set error, return early (do not call remaining tools)
4. Select the top result as `selected_item`
5. Call `suggest_outfit()` with the selected item and user's wardrobe
6. If outfit suggestion fails → set error, return early
7. Call `create_fit_card()` with the outfit and selected item
8. Return the completed session

The loop does not call all tools unconditionally — it stops and returns an error message at any point where a tool fails or returns nothing useful.

---

## State Management

**How does information from one tool get passed to the next?**
All state is stored in a single session dict initialized by `_new_session()`. Each tool's output is written to the session before the next tool is called:

- `session["parsed"]` — extracted description, size, max_price from the query
- `session["search_results"]` — full list returned by `search_listings()`
- `session["selected_item"]` — top result, passed into `suggest_outfit()`
- `session["wardrobe"]` — user's wardrobe, passed into `suggest_outfit()`
- `session["outfit_suggestion"]` — string returned by `suggest_outfit()`, passed into `create_fit_card()`
- `session["fit_card"]` — final caption returned by `create_fit_card()`
- `session["error"]` — set if any step fails; checked before each subsequent tool call

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets session["error"] with a message listing the filters applied and suggests broadening the search. Returns early — does not call suggest_outfit or create_fit_card. |
| suggest_outfit | Wardrobe is empty | Falls back to general styling advice from the LLM instead of specific combinations. Never raises an exception or returns an empty string. |
| create_fit_card | Outfit input is missing or incomplete | Returns a descriptive error string without raising an exception. LLM exceptions are caught by the agent and stored in session["error"]. |

---

## Architecture

## Architecture

```
User query (natural language)
    │
    ▼
_parse_query() ── LLM extracts description, size, max_price
    │                                                        
    ▼                                                        
session["parsed"] = {description, size, max_price}          
    │                                                        
    ▼                                                        
search_listings(description, size, max_price)               
    │       │                                               
    │       │ results=[]                                    
    │       └──► session["error"] = "No listings found..." → return session
    │                                                        
    │ results=[item, ...]                                   
    ▼                                                        
session["selected_item"] = results[0]                       
    │                                                        
    ▼                                                        
suggest_outfit(selected_item, wardrobe)                     
    │       │                                               
    │       │ wardrobe empty → general styling advice       
    │       │ exception → session["error"] → return session 
    │       │                                               
    │       └──► session["outfit_suggestion"] = "..."       
    │                                                        
    ▼                                                        
create_fit_card(outfit_suggestion, selected_item)           
    │       │                                               
    │       │ outfit empty → return error string            
    │       │ exception → session["error"] → return session 
    │       │                                               
    │       └──► session["fit_card"] = "..."                
    │                                                        
    ▼                                                        
Return completed session → app.py renders 3 UI panels
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
Used Claude with the tool specs (inputs, return values, failure modes) and the data structure from `listings.json` and `wardrobe_schema.json`. Provided the exact field names and asked Claude to implement each tool function. Verified each tool by running it in isolation from the terminal before connecting to the agent loop.

**Milestone 4 — Planning loop and state management:**
Used Claude with the completed Architecture section and State Management section above. Asked it to implement `run_agent()` matching the linear loop described. Verified by running `python3 agent.py` and checking both the happy path and no-results path before testing in the UI.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
`_parse_query()` sends the query to the LLM and extracts: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`. These are stored in `session["parsed"]`.

**Step 2:**
`search_listings("vintage graphic tee", size=None, max_price=30.0)` loads all 40 listings, filters out anything over $30, scores remaining items by keyword overlap with "vintage graphic tee", and returns a ranked list. Top result: Y2K Baby Tee — Butterfly Print, $18, depop. Stored in `session["search_results"]` and `session["selected_item"]`.

**Step 3:**
`suggest_outfit(new_item=<Y2K Baby Tee>, wardrobe=<example wardrobe>)` formats the wardrobe items into a prompt and asks the LLM to suggest outfit combinations. Returns two outfits: one streetwear (baggy jeans + chunky sneakers) and one cottagecore-grunge (khaki trousers + combat boots + denim jacket). Stored in `session["outfit_suggestion"]`.

**Step 4:**
`create_fit_card(outfit=<suggestion>, new_item=<Y2K Baby Tee>)` asks the LLM to write a casual Instagram caption mentioning the item, price, and platform. Returns: "Just threw on my new fave Y2K Baby Tee (scored it for $18.0 on Depop)..." Stored in `session["fit_card"]`.

**Final output to user:**
Three panels in the UI — the listing details, the outfit suggestion, and the fit card caption.

**Error path:**
If the user searches for "designer ballgown size XXS under $5", `search_listings` returns an empty list. The agent sets `session["error"]` to a message explaining no results were found with those filters and suggests broadening the search. `suggest_outfit` and `create_fit_card` are never called.