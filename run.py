"""
run.py — Run the agent from the terminal.
Run:     python run.py            (saves the report in reports/)
Print:   python run.py --print    (also shows the report in the terminal)
Diagram: python run.py --diagram
"""
import json
import sys
from pathlib import Path

from src.graph import build_graph


def main() -> None:
    app = build_graph()

    if "--diagram" in sys.argv:
        print(app.get_graph().draw_mermaid())  # paste into the README
        return

    profile = json.loads(Path("data/sample_profile.json").read_text(encoding="utf-8"))
    result = app.invoke({
        "programme": {
            "university": "University of Groningen",
            "name": "Artificial Intelligence",
            "degree": "bachelor",
            "country": "NL",
            "domain": "rug.nl",
        },
        "intake": profile["target_intake"],
        "profile": profile,
    })

    print("\n".join(result["log"]))
    if "--print" in sys.argv:
        print("\n" + result["report_md"])   # show the whole report in the terminal


if __name__ == "__main__":
    main()