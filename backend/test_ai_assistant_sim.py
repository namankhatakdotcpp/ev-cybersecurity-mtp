"""
Simulated test runner for the EVChargingGame AI assistant.

Purpose:
- Test assistant prompt assembly and recommendation flow without BeamNG.
- Feed simulated station layout, screenshot analysis, and charging history.
- Optionally avoid external LLM/VLM API calls (default behavior).

Usage examples:
  python test_ai_assistant_sim.py
  python test_ai_assistant_sim.py --runs 5 --mock-vision
  python test_ai_assistant_sim.py --question "Which kiosk is safest?"
  python test_ai_assistant_sim.py --real-llm --runs 3
  python test_ai_assistant_sim.py --disable-rag
"""

import argparse
import json
import random
from typing import Any, Dict, List

from ai_assistant import AIAssistant


DEEPFAKE_IMAGES = [
    "deepfake1.png",
    "deepfake2.png",
    "deepfake6.png",
    "deepfake7.png",
    "deepfake8.png",
    "deepfake9.png",
]

REAL_IMAGES = [
    "real4.png",
    "real6.png",
    "real7.png",
    "real8.png",
    "real9.png",
]


def _random_station_entry(kiosk_id: int, occupied_indices: List[int]) -> Dict[str, Any]:
    is_occupied = kiosk_id in occupied_indices
    station: Dict[str, Any] = {
        "id": kiosk_id + 1,
        "name": f"Kiosk {kiosk_id + 1}",
        "status": "Occupied" if is_occupied else "Available",
        "image": None,
        "attack": None,
        "cyber_attack_mode": None,
        "discount_coupon": False,
        "mobile_upi": "",
        "charge_amount": "",
    }

    if is_occupied:
        return station

    if random.random() < 0.5:
        station["image"] = random.choice(DEEPFAKE_IMAGES)
        station["attack"] = "Cyber Attack" if random.random() < 0.8 else "Safe"
    else:
        station["image"] = random.choice(REAL_IMAGES)
        station["attack"] = "Cyber Attack" if random.random() < 0.2 else "Safe"

    if station["attack"] == "Cyber Attack":
        station["cyber_attack_mode"] = "blocked" if random.random() < 0.2 else "reduced"

    station["discount_coupon"] = random.random() < 0.2
    return station


def build_simulated_layout(station_number: int = 7) -> Dict[str, Any]:
    num_occupied = 1 if random.random() < 0.5 else 0
    occupied_indices = random.sample(range(3), num_occupied) if num_occupied > 0 else []
    stations = [_random_station_entry(i, occupied_indices) for i in range(3)]

    return {
        "route": "StationLayout",
        "Message": "StationGenerated",
        "Station": station_number,
        "page": "station",
        "charge": random.randint(20, 40),
        "points": random.randint(120, 400),
        "imageProb": True,
        "stations": stations,
    }


def build_mock_screenshot_json() -> str:
    return json.dumps(
        {
            "Kiosk 1": {
                "Visual Content": "Coupon with synthetic-looking face and exaggerated 70% discount claim.",
                "Anomalies": "Possible deepfake imagery and unrealistic promotional discount.",
            },
            "Kiosk 2": {
                "Visual Content": "Occupied",
                "Anomalies": "None",
            },
            "Kiosk 3": {
                "Visual Content": "Branded charging coupon with realistic vehicle image and consistent typography.",
                "Anomalies": "No obvious cyberattack indicators.",
            },
        },
        ensure_ascii=False,
    )


def install_mock_llm(assistant: AIAssistant) -> None:
    def _fake_invoke(prompt: str) -> str:
        # Deterministic fake answer so end-to-end flow can run without API keys.
        if "Kiosk 3" in prompt and "Kiosk 1" in prompt:
            return (
                "Kiosk 3 appears to be the safest available option right now. "
                "Kiosk 1 shows suspicious signals (synthetic visual style and unrealistic offer), "
                "while Kiosk 2 is occupied. If your charge is sufficient, skip is also acceptable, "
                "but if you need charging now, use Kiosk 3."
            )
        return "Based on available context, choose the least risky available kiosk."

    assistant._invoke_llm = _fake_invoke


def seed_previous_charging_events(assistant: AIAssistant) -> None:
    assistant.current_screenshot_context = json.dumps(
        {
            "Kiosk 1": {"Visual Content": "Suspicious promo", "Anomalies": "Deepfake-like face"},
            "Kiosk 2": {"Visual Content": "Occupied", "Anomalies": "None"},
            "Kiosk 3": {"Visual Content": "Legit poster", "Anomalies": "None"},
        }
    )

    assistant.record_charging_event(
        trial=5,
        kiosk_used=1,
        kiosk_attack="Cyber Attack",
        charge_amount=30,
        points_after=190,
        ending_charge=47,
    )
    assistant.record_charging_event(
        trial=6,
        kiosk_used=3,
        kiosk_attack="Safe",
        charge_amount=24,
        points_after=166,
        ending_charge=58,
    )


def simulate_random_kiosk_pick(layout: Dict[str, Any]) -> Dict[str, Any]:
    kiosks: List[Dict[str, Any]] = layout.get("stations", [])
    if not kiosks:
        return {
            "kiosk_used": None,
            "kiosk_attack": "Safe",
            "charge_amount": 0,
            "points_after": float(layout.get("points", 0)),
            "ending_charge": float(layout.get("charge", 0)),
        }

    available_kiosks = [k for k in kiosks if str(k.get("status", "")).strip().lower() != "occupied"]
    if not available_kiosks:
        return {
            "kiosk_used": None,
            "kiosk_attack": "Safe",
            "charge_amount": 0,
            "points_after": float(layout.get("points", 0)),
            "ending_charge": float(layout.get("charge", 0)),
        }

    picked = random.choice(available_kiosks)
    kiosk_used = int(picked.get("id", 0)) or None
    start_points = float(layout.get("points", 0))
    start_charge = float(layout.get("charge", 0))

    charge_amount = random.randint(12, 35)
    points_after = max(0.0, start_points - charge_amount)
    ending_charge = min(100.0, start_charge + charge_amount)
    kiosk_attack = str(picked.get("attack") or "Safe")

    return {
        "kiosk_used": kiosk_used,
        "kiosk_attack": kiosk_attack,
        "charge_amount": charge_amount,
        "points_after": points_after,
        "ending_charge": ending_charge,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a simulated AI assistant test.")
    parser.add_argument("--question", default="Which kiosk should I pick at this station and why?")
    parser.add_argument("--real-llm", action="store_true", help="Use real LLM API call instead of mocked reply")
    parser.add_argument("--mock-vision", action="store_true", help="Use mocked screenshot JSON instead of renderer+screenshot+vision")
    parser.add_argument("--disable-rag", action="store_true", help="Disable RAG for this simulation run")
    parser.add_argument("--show-prompt", action="store_true", help="Print the full assembled prompt")
    parser.add_argument("--runs", type=int, default=1, help="Number of random simulated layouts to run")
    parser.add_argument("--start-station", type=int, default=7, help="Starting station number for simulations")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducible layouts")
    args = parser.parse_args()

    if args.runs < 1:
        raise ValueError("--runs must be at least 1")

    if args.seed is not None:
        random.seed(args.seed)

    assistant = AIAssistant(rag_enabled=not args.disable_rag)

    if not args.real_llm:
        install_mock_llm(assistant)

    seed_previous_charging_events(assistant)

    for run_idx in range(args.runs):
        station_number = args.start_station + run_idx
        layout = build_simulated_layout(station_number=station_number)

        if args.mock_vision:
            description = build_mock_screenshot_json()
            assistant.current_screenshot_context = description
            assistant.screenshot_history[str(layout["Station"])] = description
        else:
            description = assistant.on_new_station(layout)

        print(f"\n=== Run {run_idx + 1}/{args.runs} | Station {station_number} ===")
        print("\n=== Simulated Screenshot Analysis ===")
        print(description)

        result = assistant.ask(
            message=args.question,
            current_charge=layout["charge"],
            points=layout["points"],
            trial=layout["Station"],
        )

        print("\n=== Assistant Reply ===")
        print(result.get("reply", ""))

        simulated_pick = simulate_random_kiosk_pick(layout)
        if simulated_pick["kiosk_used"] is None:
            print("\n=== Simulated Charging Event Skipped ===\nNo available kiosk to pick.")
            continue

        assistant.record_charging_event(
            trial=layout["Station"],
            kiosk_used=simulated_pick["kiosk_used"],
            kiosk_attack=simulated_pick["kiosk_attack"],
            charge_amount=simulated_pick["charge_amount"],
            points_after=simulated_pick["points_after"],
            ending_charge=simulated_pick["ending_charge"],
        )
        print(
            "\n=== Simulated Charging Event Saved ===\n"
            f"Kiosk: {simulated_pick['kiosk_used']} | "
            f"Attack: {simulated_pick['kiosk_attack']} | "
            f"Charge Added: {simulated_pick['charge_amount']} | "
            f"Points After: {int(simulated_pick['points_after'])} | "
            f"Ending Charge: {int(simulated_pick['ending_charge'])}%"
        )

        if args.show_prompt:
            print("\n=== Full Prompt Sent to LLM ===")
            print(result.get("prompt", ""))


if __name__ == "__main__":
    main()
