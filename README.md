# pokemon

Simple CLI to fetch Pokémon data from the public PokeAPI, a small Vue web UI, and an optional Flask backend.

Web (Vue.js) — no build required
- Open index.html in your browser.
- Use the selectors: first choose a Generation, then select a Pokémon from that generation and click "Load".
- The page will fetch https://pokeapi.co/api/v2/generation to list generations, then https://pokeapi.co/api/v2/generation/<id> for species, and finally https://pokeapi.co/api/v2/pokemon/<pokemon_name> to render the info.
- Works as a static file (no server needed). Uses Vue 3 via CDN and the browser Fetch API.
  - Visualizations: Base stats radar chart (Chart.js), sprite gallery (front/back, shiny, female when available), type-colored badges, and inline audio players for cries.

Optional backend (Flask)
- You can run a tiny backend to reduce JavaScript in the frontend and avoid doing client-side mapping/ID extraction.
- Start it:
  - pip install -r requirements.txt
  - python app.py
- Then open http://127.0.0.1:5000/ — it serves index.html and exposes helpful JSON endpoints under /api:
  - GET /api/generations → { results: [{ id, name, url }] }
  - GET /api/generation/<id>/species → { results: [{ id, name, sprite }] } (sprite URL precomputed)
  - GET /api/pokemon/<name_or_id> → passes through the PokeAPI response
  - GET /api/pokemon/<name_or_id>/summary → returns a concise text summary (using the CLI’s summarize_pokemon)

Notes on architecture
- Originally, the Python code was a CLI tool (not a web backend). The Vue page is the frontend. The optional Flask app turns the Python side into a backend so the frontend can be thinner.

What this does
- Calls https://pokeapi.co/api/v2/pokemon/{name_or_id} (for example: pikachu)
- Prints a human-friendly summary including:
  - core: name, id, height, weight, base experience, order, is_default
  - species (name/url), encounters URL
  - types with slots, abilities with hidden/slot flags
  - base stats
  - primary sprite URL plus additional sprite variants when available (front/back, shiny, female)
  - forms and held items
- Optionally prints raw JSON

CLI quick start
1. Ensure you have Python 3.9+ installed.
2. Install dependencies:
   - pip install -r requirements.txt
3. Run:
   - Interactive (you'll be prompted for a name or id):
     - python main.py
   - Or pass the name/id directly:
     - python main.py pikachu
4. Fetch a different Pokémon (by name or id):
   - python main.py bulbasaur
   - python main.py 25
5. Print raw JSON instead of the summary:
   - python main.py pikachu --raw-json

Notes
- If you don't pass a name/id, the script will ask you to type one interactively.
- The tool uses a 10s network timeout by default. You can change it with --timeout, e.g.: python main.py pikachu --timeout 5
- The value you pass (name or numeric id) is appended as the last segment to the base API URL: https://pokeapi.co/api/v2/pokemon/<your_input>
- API reference: https://pokeapi.co/

Tip
- For the web page, you can also serve it locally (optional) using a simple static server if your browser blocks local file audio for cries links. For example, with Python: python -m http.server 8000 and then open http://localhost:8000/index.html

Web UI details
- Generation selector loads from https://pokeapi.co/api/v2/generation?limit=100.
- Pokémon selector is populated from the selected generation’s pokemon_species list and sorted alphabetically.
- The fetch uses the species name as the last path segment of https://pokeapi.co/api/v2/pokemon/<name>.
- Errors and loading states are shown inline in the page.
 - Visualizations:
   - Base stats radar chart using Chart.js.
   - Sprites gallery with thumbnails for front/back and shiny/female variants when available.
   - Type chips are color-coded per Pokémon type for quick recognition.
   - Cries can be played inline with audio controls (browser autoplay policies may require user interaction).

Using the backend to simplify the frontend
- If you prefer, change the frontend fetch URLs to the local backend:
  - Generations: /api/generations
  - Species: /api/generation/<id>/species (already includes sprite URLs and normalized ids)
  - Pokémon: /api/pokemon/<name>
  - Optional text summary: /api/pokemon/<name>/summary
- This removes the need for client-side regex/id extraction and sprite URL construction.