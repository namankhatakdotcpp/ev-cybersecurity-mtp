import base64
import csv
import json
import os
import random
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


ANALYSIS_PROMPT = """
You are an expert in analyzing EV charging network user interfaces for signs of potential cyberattacks.
Analyze the given interface carefully.
For each Kiosk section (Kiosk 1, Kiosk 2, Kiosk 3):
Describe the visual content shown in its promotion or coupon area (images, graphics, text, faces, QR codes, etc.).
Identify any anomalies or signs of cyberattack, such as deepfake or AI-generated images, unrealistic discounts, phishing prompts, or suspicious branding.

If a kiosk's status is Occupied, simply output "Visual Content": "Occupied" and "Anomalies": "None".
If no images or graphics appear, write "Visual Content": "No visual content available".

Return the result strictly in JSON format as:
{
    "Kiosk 1": {
        "Visual Content": "...",
        "Anomalies": "..."
    },
    "Kiosk 2": {
        "Visual Content": "...",
        "Anomalies": "..."
    },
    "Kiosk 3": {
        "Visual Content": "...",
        "Anomalies": "..."
    }
}
""".strip()


def _strip_code_fence(text: str) -> str:
    out = (text or "").strip()
    if out.startswith("```"):
        out = out.strip("`")
        if out.lower().startswith("json"):
            out = out[4:].strip()
    return out


class ScreenshotAnalyzer:
    def __init__(self) -> None:
        this_dir = os.path.dirname(os.path.abspath(__file__))
        self.mode = os.environ.get("SCREENSHOT_ANALYSIS_MODE", "gemini").strip().lower()
        csv_setting = os.environ.get(
            "SCREENSHOT_ANALYSIS_CSV",
            os.path.join(this_dir, "screenshot_analysis_samples.csv"),
        )
        self.csv_path = csv_setting if os.path.isabs(csv_setting) else os.path.join(this_dir, csv_setting)

        self._gemini_client = None
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            try:
                from google import genai

                self._gemini_client = genai.Client(api_key=api_key)
                print("[ScreenshotAnalyzer] Gemini Vision client ready")
            except Exception as e:
                print(f"[ScreenshotAnalyzer] Gemini Vision init failed: {e}")

        self._csv_rows_by_image: Dict[str, List[Dict[str, str]]] = {}
        self._csv_loaded = False

        print(f"[ScreenshotAnalyzer] Mode selected: {self.mode}")

    def analyze(self, image_path: str, layout: Dict[str, Any]) -> str:
        image_names = self._collect_image_names(layout)

        if self.mode in {"gemini", "google"}:
            text = self._analyze_with_gemini(image_path, image_names=image_names)
            self._persist_analysis_rows(layout, text)
            return text
        if self.mode in {"qwen", "qwen-vl", "qwen32b"}:
            text = self._analyze_with_qwen_local(image_path, image_names=image_names)
            self._persist_analysis_rows(layout, text)
            return text
        if self.mode in {"csv", "csv-random", "replay"}:
            return self._analyze_with_csv_random(layout)

        return (
            "Invalid SCREENSHOT_ANALYSIS_MODE. "
            "Use one of: gemini, qwen, csv."
        )

    def _analyze_with_gemini(self, image_path: str, image_names: List[str]) -> str:
        if not self._gemini_client:
            return "UI rendering available but Gemini Vision is not configured (missing GEMINI_API_KEY)."

        if self._contains_any_name(ANALYSIS_PROMPT, image_names):
            return "Safety check failed: image filename detected in Gemini prompt."

        try:
            from PIL import Image

            img = Image.open(image_path).convert("RGB")
            response = self._gemini_client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=[ANALYSIS_PROMPT, img],
            )
            text = (getattr(response, "text", None) or "").strip()
            return _strip_code_fence(text)
        except Exception as e:
            return f"Gemini vision analysis failed: {e}"

    def _analyze_with_qwen_local(self, image_path: str, image_names: List[str]) -> str:
        model = os.environ.get("QWEN_VL_MODEL", "qwen2.5vl:32b")
        endpoint = os.environ.get("QWEN_VL_ENDPOINT", "http://127.0.0.1:11434/api/generate")

        try:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("ascii")
        except Exception as e:
            return f"Qwen local analysis failed while reading screenshot: {e}"

        payload = {
            "model": model,
            "prompt": ANALYSIS_PROMPT + "\nReturn only valid JSON with the exact kiosk keys.",
            "images": [image_b64],
            "stream": False,
        }

        if self._contains_any_name(str(payload.get("prompt", "")), image_names):
            return "Safety check failed: image filename detected in Qwen prompt."

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                text = str(data.get("response", "")).strip()
                if not text:
                    return "Qwen local analysis returned empty response."
                return _strip_code_fence(text)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            return f"Qwen local analysis HTTP error {e.code}: {body}"
        except Exception as e:
            return f"Qwen local analysis failed: {e}"

    def _load_csv_rows(self) -> None:
        if self._csv_loaded:
            return

        rows_by_image: Dict[str, List[Dict[str, str]]] = {}
        if os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        image_name = (row.get("imageName") or "").strip().lower()
                        if not image_name:
                            continue
                        rows_by_image.setdefault(image_name, []).append(
                            {
                                "visualContext": (row.get("visualContext") or "").strip(),
                                "Anomalies": (row.get("Anomalies") or "").strip(),
                            }
                        )
            except Exception as e:
                print(f"[ScreenshotAnalyzer] Failed to load CSV replay file: {e}")

        self._csv_rows_by_image = rows_by_image
        self._csv_loaded = True

    def _pick_csv_row(self, image_name: str) -> Optional[Dict[str, str]]:
        self._load_csv_rows()
        candidates = self._csv_rows_by_image.get((image_name or "").strip().lower(), [])
        if not candidates:
            return None
        return random.choice(candidates)

    def _collect_image_names(self, layout: Dict[str, Any]) -> List[str]:
        stations: List[Dict[str, Any]] = layout.get("stations", [])
        image_prob = bool(layout.get("imageProb", False))
        names: List[str] = []
        for station in stations:
            if self._coupon_display_state(station, image_prob) != "coupon_image":
                continue
            image_name = str(station.get("image") or "").strip()
            if image_name:
                names.append(image_name)
        return names

    def _coupon_display_state(self, station: Dict[str, Any], image_prob: bool) -> str:
        status = str(station.get("status", "")).strip().lower()
        if status == "occupied":
            return "occupied"

        explicit = str(station.get("coupon_display_state", "")).strip().lower()
        if explicit in {"coupon_image", "no_coupon", "occupied"}:
            return explicit

        image_name = str(station.get("image") or "").strip()
        return "coupon_image" if (image_prob and image_name) else "no_coupon"

    def _contains_any_name(self, text: str, image_names: List[str]) -> bool:
        lowered = (text or "").lower()
        for name in image_names:
            token = (name or "").strip().lower()
            if token and token in lowered:
                return True
        return False

    def _persist_analysis_rows(self, layout: Dict[str, Any], analysis_text: str) -> None:
        try:
            parsed = json.loads(analysis_text)
        except Exception:
            return

        stations: List[Dict[str, Any]] = layout.get("stations", [])
        image_prob = bool(layout.get("imageProb", False))
        rows_to_append: List[Dict[str, str]] = []

        for idx, station in enumerate(stations, start=1):
            if self._coupon_display_state(station, image_prob) != "coupon_image":
                continue
            image_name = str(station.get("image") or "").strip()
            if not image_name:
                continue

            kiosk_key = f"Kiosk {idx}"
            kiosk_data = parsed.get(kiosk_key, {}) if isinstance(parsed, dict) else {}
            visual = str(kiosk_data.get("Visual Content", "")).strip()
            anomalies = str(kiosk_data.get("Anomalies", "")).strip()
            if not visual and not anomalies:
                continue

            rows_to_append.append(
                {
                    "imageName": image_name,
                    "visualContext": visual,
                    "Anomalies": anomalies,
                }
            )

        if not rows_to_append:
            return

        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        write_header = not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0
        with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["imageName", "visualContext", "Anomalies"])
            if write_header:
                writer.writeheader()
            writer.writerows(rows_to_append)

        self._csv_loaded = False

    def _analyze_with_csv_random(self, layout: Dict[str, Any]) -> str:
        stations: List[Dict[str, Any]] = layout.get("stations", [])
        image_prob = bool(layout.get("imageProb", False))
        result: Dict[str, Dict[str, str]] = {}

        for idx, station in enumerate(stations, start=1):
            kiosk_key = f"Kiosk {idx}"
            coupon_state = self._coupon_display_state(station, image_prob)
            image_name = str(station.get("image") or "").strip()

            if coupon_state == "occupied":
                result[kiosk_key] = {
                    "Visual Content": "Occupied",
                    "Anomalies": "None",
                }
                continue

            if coupon_state == "no_coupon":
                result[kiosk_key] = {
                    "Visual Content": "No coupon shown; kiosk displays no active promotions.",
                    "Anomalies": "None",
                }
                continue

            if coupon_state != "coupon_image" or not image_name:
                result[kiosk_key] = {
                    "Visual Content": "No visual content available",
                    "Anomalies": "None",
                }
                continue

            selected = self._pick_csv_row(image_name)
            if not selected:
                result[kiosk_key] = {
                    "Visual Content": f"No replay row found in CSV for {image_name}",
                    "Anomalies": "Unknown",
                }
                continue

            result[kiosk_key] = {
                "Visual Content": selected.get("visualContext", "No visual content available"),
                "Anomalies": selected.get("Anomalies", "None"),
            }

        for idx in range(len(stations) + 1, 4):
            result[f"Kiosk {idx}"] = {
                "Visual Content": "No visual content available",
                "Anomalies": "None",
            }

        return json.dumps(result, ensure_ascii=False, indent=2)
