"""
Standalone test for the D017 automation-bias condition addition to AIAssistant.
Builds the SAME synthetic kiosk state and runs it through all three conditions
(safe / malicious / absent) to show the prompt and reply difference directly.

Does NOT touch the shared RAG store: constructed with rag_enabled=False.
Run from backend/: python3 test_automation_bias_conditions.py
"""
import json

from ai_assistant import AIAssistant

# Same kiosk state for all three conditions, so the only variable is `condition`.
STATION_LAYOUT = {"Station": 7}
SCREENSHOT_ANALYSIS = json.dumps({
    "Kiosk 1": {"Visual Content": "Legit 10% discount poster", "Anomalies": "None"},
    "Kiosk 2": {"Visual Content": "Suspicious oversized discount banner, inconsistent logo", "Anomalies": "Deepfake-like promo image, unrealistic 60% discount"},
    "Kiosk 3": {"Visual Content": "Occupied", "Anomalies": "None"},
})


def make_assistant() -> AIAssistant:
    ai = AIAssistant(rag_enabled=False, incident_mode=True)
    # Seed the same verified screenshot context ai_assistant.py would have from a real
    # on_new_station() call, without actually rendering/screenshotting anything.
    ai.current_screenshot_station = "7"
    ai.current_screenshot_context = SCREENSHOT_ANALYSIS
    ai.screenshot_history["7"] = SCREENSHOT_ANALYSIS
    return ai


def run_condition(condition: str, target: int = None):
    ai = make_assistant()
    print("\n" + "=" * 78)
    print(f"CONDITION = {condition!r}" + (f"  target_kiosk={target}" if target else ""))
    print("=" * 78)
    result = ai.ask(
        message="Recommend the safest available kiosk for this station and briefly explain why.",
        current_charge=55.0,
        points=210.0,
        trial=7,
        condition=condition,
        malicious_target_kiosk=target,
    )
    print("\n--- Returned dict keys:", list(result.keys()), "---")
    print("condition field:", result.get("condition"))
    print("malicious_target_kiosk field:", result.get("malicious_target_kiosk"))
    if result.get("prompt"):
        print("\n--- Tail of prompt actually sent to the LLM (last 600 chars) ---")
        print(result["prompt"][-600:])
    print("\n--- Reply ---")
    print(result["reply"])
    return result


if __name__ == "__main__":
    run_condition("safe")
    run_condition("malicious", target=2)  # Kiosk 2 is the one with real anomalies flagged
    run_condition("absent")

    print("\n" + "=" * 78)
    print("Fail-safe check: condition='malicious' with NO target kiosk must raise, not silently pick one.")
    print("=" * 78)
    try:
        run_condition("malicious", target=None)
        print("FAIL: did not raise")
    except ValueError as e:
        print(f"OK - raised as expected: {e}")
