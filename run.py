"""
run.py — Run the agent from the terminal.
Run:     python run.py groningen      (saves the report in reports/)
         python run.py tum
Print:   python run.py tum --print    (also shows the report in the terminal)
Diagram: python run.py --diagram
The programmes are listed in data/programmes.json; the student profile in data/sample_profile.json.
"""
import json
import sys
from pathlib import Path

from src.graph import build_graph, run_agent


def main() -> None:
    if "--diagram" in sys.argv:
        print(build_graph().get_graph().draw_mermaid())  # paste into the README
        return

    programmes = json.loads(Path("data/programmes.json").read_text(encoding="utf-8"))
    keys = [a for a in sys.argv[1:] if not a.startswith("--")]
    key = keys[0] if keys else "groningen"
    if key not in programmes:
        print(f"Unknown programme '{key}'. Choose one of: {', '.join(programmes)}")
        return

    profile = json.loads(Path("data/sample_profile.json").read_text(encoding="utf-8"))
    result = run_agent(programmes[key], profile)

    print("\n".join(result["log"]))
    if "--print" in sys.argv:
        print("\n" + result["report_md"])   # show the whole report in the terminal


if __name__ == "__main__":
    main()
