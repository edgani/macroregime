"""CLI entry point for EROS Warroom.
Usage: python run.py
"""
from final_core.production_entry import run
from final_core.build_dashboard import build_dashboard
import json

if __name__ == "__main__":
    result = run()
    dash = build_dashboard()
    print(json.dumps({
        "system_status": result.get("system_status"),
        "current_action": result.get("current_action"),
        "scenario_count": result.get("scenario_count"),
        "qualified_opportunity_count": len(result.get("qualified_opportunities", [])),
        "dashboard": str(dash),
    }, indent=2))
