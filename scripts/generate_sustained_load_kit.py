"""
Regenerate tests/performance/sustained_load.json: a note plus 60 flippable cards named
card1..card60 (see sustained_load.py's execute_worker: my_card_name = f'card{idx+1}'),
laid out in a 10x6 grid that fits the 1366x768 window tests/e2e/conftest.py's
browser_func opens (verified by screenshot - browser_func does not call
set_window_size, unlike the e2e suite's fixtures, so it keeps headless Firefox's
default viewport).

Cards are half height (60px, vs. a normal card's 120px) purely to compress the grid
vertically - 6 rows of full-height cards ran off the bottom of that viewport.

60 is a fixed headroom over any worker count this project's load tests actually run
(currently up to 29) - not sized to the run. Bump it here and rerun if a future config
needs more.

Run: python scripts/generate_sustained_load_kit.py
"""
import json
from pathlib import Path

CARD_COUNT = 60
COLUMNS = 10
COLUMN_PITCH = 100  # card width 75px + gap
CARD_HEIGHT = 60  # half of a normal card's 120px, to compress the grid vertically
ROW_PITCH = 70  # CARD_HEIGHT + gap

OUT_FILE = Path(__file__).parent.parent / "tests/performance/sustained_load.json"


def build_kit():
    components = {
        "NOTE": {
            "color": "blue", "draggable": True, "flippable": False, "height": "30px",
            "left": "0px", "name": "note", "ownable": False, "resizable": False,
            "showImage": False, "text": "Table for sustained load testing!",
            "top": "0px", "width": "200px", "zIndex": 1,
        },
    }
    for i in range(1, CARD_COUNT + 1):
        col = (i - 1) % COLUMNS
        row = (i - 1) // COLUMNS
        components[f"C{i:03d}"] = {
            "color": "yellow", "textColor": "black", "draggable": True, "flippable": True,
            "height": f"{CARD_HEIGHT}px", "left": f"{col * COLUMN_PITCH}px", "name": f"card{i}",
            "ownable": False, "resizable": False, "showImage": False,
            "faceupText": "UP", "facedownText": "DOWN",
            "top": f"{100 + row * ROW_PITCH}px", "width": "75px", "zIndex": i + 1,
        }
    return {"components": components, "kits": [], "players": {}}


if __name__ == "__main__":
    with open(OUT_FILE, "w") as f:
        json.dump(build_kit(), f, indent=2)
        f.write("\n")
    print(f"wrote {OUT_FILE}")
