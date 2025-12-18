# pokemon

Simple CLI to fetch Pokémon data from the public PokeAPI.

Web (Vue.js) — no build required
- Open index.html in your browser.
- Type a Pokémon name or numeric ID into the textbox and press Enter (or click Search).
- The page will fetch https://pokeapi.co/api/v2/pokemon/<your_input> and render the info.
- Works as a static file (no server needed). Uses Vue 3 via CDN and the browser Fetch API.
- 
**You can also view the app live here:** https://bathorian.github.io/pokemon/

What this does
- Calls `https://pokeapi.co/api/v2/pokemon/{name_or_id}` (for example: `pikachu`)
- Prints a human-friendly summary including:
  - core: name, id, height, weight, base experience, order, is_default
  - species (name/url), encounters URL
  - types with slots, abilities with hidden/slot flags
  - base stats
  - primary sprite URL plus additional sprite variants when available (front/back, shiny, female)
  - forms and held items
- Optionally prints raw JSON

Quick start
1. Ensure you have Python 3.9+ installed.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run:
   - Interactive (you'll be prompted for a name or id):
     - `python main.py`
   - Or pass the name/id directly:
     - `python main.py pikachu`
4. Fetch a different Pokémon (by name or id):
   - `python main.py bulbasaur`
   - `python main.py 25`
5. Print raw JSON instead of the summary:
   - `python main.py pikachu --raw-json`

Notes
- If you don't pass a name/id, the script will ask you to type one interactively.
- The tool uses a 10s network timeout by default. You can change it with `--timeout`, e.g.: `python main.py pikachu --timeout 5`.
- The value you pass (name or numeric id) is appended as the last segment to the base API URL: `https://pokeapi.co/api/v2/pokemon/<your_input>`
- API reference: https://pokeapi.co/

Tip
- For the web page, you can also serve it locally (optional) using a simple static server if your browser blocks audio playback from local files (e.g., for cry links). For example, with Python: `python -m http.server 8000` and then open http://localhost:8000/index.html

About this README
- This README was generated and refined with the assistance of an AI tool. While care was taken to ensure accuracy, it may contain mistakes or omissions. If you notice anything off, please open an issue or submit a pull request.