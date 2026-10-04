import json
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

from screenshot_analyzers import ScreenshotAnalyzer


def _safe(s: Any) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class UIRenderer:
    """Render station UI in a browser, capture screenshot, and run configurable analysis."""

    def __init__(self) -> None:
        this_dir = os.path.dirname(os.path.abspath(__file__))
        self.images_dir = os.path.join(this_dir, "images")
        self.screenshots_dir = os.path.join(this_dir, "screenshots")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
        self.analyzer = ScreenshotAnalyzer()

    def _image_src(self, file_name: Optional[str]) -> str:
        if not file_name:
            return ""
        folder = "deepfake" if "deepfake" in file_name.lower() else "real"
        path = os.path.join(self.images_dir, folder, file_name)
        return "file:///" + path.replace("\\", "/")

    def _coupon_display_state(self, station: Dict[str, Any], image_prob: bool) -> str:
        status = str(station.get("status", "")).strip().lower()
        if status == "occupied":
            return "occupied"

        explicit = str(station.get("coupon_display_state", "")).strip().lower()
        if explicit in {"coupon_image", "no_coupon", "occupied"}:
            return explicit

        image_name = str(station.get("image") or "").strip()
        return "coupon_image" if (image_prob and image_name) else "no_coupon"

    def _render_html(self, layout: Dict[str, Any]) -> str:
        stations: List[Dict[str, Any]] = layout.get("stations", [])
        trial = layout.get("Station", "?")
        charge = layout.get("charge", 0)
        points = layout.get("points", 0)
        image_prob = bool(layout.get("imageProb", False))

        card_html = []
        for station in stations:
            status = station.get("status", "Unknown")
            title = _safe(station.get("name", f"Kiosk {station.get('id', '?')}"))
            coupon_state = self._coupon_display_state(station, image_prob)

            banner = ""
            if coupon_state == "coupon_image":
                banner = "<div class='banner'>Special 10% Discount Available!</div>"

            if coupon_state == "occupied":
                media = "<div class='empty'>No Active Promotions</div>"
            elif coupon_state == "coupon_image" and station.get("image"):
                img_src = self._image_src(station.get("image"))
                media = f"<img class='coupon' src='{img_src}' alt='coupon'/>"
            else:
                media = "<div class='empty'>No visual content available</div>"

            card_html.append(
                f"""
                <section class='card'>
                  <h3>{title}</h3>
                  <div class='status'>{_safe(status)}</div>
                  {banner}
                  {media}
                </section>
                """
            )

        cards = "\n".join(card_html)
        return f"""
<!doctype html>
<html>
<head>
<meta charset='utf-8'/>
<title>EV Station Snapshot</title>
<style>
body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: linear-gradient(135deg,#1e3c72,#2a5298,#4CAF50); color: #124; }}
.shell {{ padding: 16px; width: 1280px; height: 800px; box-sizing: border-box; }}
.top {{ display:flex; justify-content:space-between; background:#fff; border-radius:12px; padding:12px 16px; margin-bottom:12px; }}
.grid {{ display:grid; grid-template-columns: repeat(3,1fr); gap:12px; }}
.card {{ background:#f8fafc; border:2px solid #84cc16; border-radius:14px; padding:12px; min-height:630px; }}
.card h3 {{ margin:0 0 8px 0; color:#166534; text-align:center; }}
.status {{ text-align:center; margin-bottom:8px; font-weight:700; }}
.banner {{ background:#facc15; border-radius:18px; text-align:center; padding:8px; margin-bottom:8px; font-weight:700; }}
.coupon {{ width:100%; max-height:360px; height:auto; object-fit:contain; border-radius:12px; border:2px solid #22c55e; background:#e2e8f0; }}
.empty {{ height:360px; border:2px dashed #94a3b8; border-radius:12px; display:flex; align-items:center; justify-content:center; color:#64748b; }}
</style>
</head>
<body>
  <div class='shell'>
    <div class='top'>
      <div><strong>Station {trial}</strong></div>
      <div><strong>Charge:</strong> {int(float(charge))}%</div>
      <div><strong>Points:</strong> {int(float(points))}</div>
    </div>
    <div class='grid'>{cards}</div>
  </div>
</body>
</html>
"""

    def render_and_capture(self, layout: Dict[str, Any]) -> Optional[str]:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
        except Exception:
            print("[UIRenderer] selenium not installed. Install with: pip install selenium")
            return None

        html_content = self._render_html(layout)
        fd, temp_path = tempfile.mkstemp(prefix="_temp_station_", suffix=".html")
        os.close(fd)
        screenshot_path = os.path.join(
            self.screenshots_dir,
            f"station_{layout.get('Station', 'x')}_{int(time.time()*1000)}.png",
        )

        driver = None
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            options = ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1280,800")
            options.add_argument("--force-device-scale-factor=1")
            options.add_argument("--hide-scrollbars")

            driver = webdriver.Chrome(options=options)
            file_url = "file:///" + temp_path.replace("\\", "/")
            driver.get(file_url)
            time.sleep(0.35)
            driver.save_screenshot(screenshot_path)
            print(f"[UIRenderer] Screenshot captured: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"[UIRenderer] Screenshot capture failed: {e}")
            return None
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def analyze_screenshot(self, image_path: str, layout: Dict[str, Any]) -> str:
        return self.analyzer.analyze(image_path=image_path, layout=layout)

    def _fallback_to_csv_inference(self, layout: Dict[str, Any], reason: str) -> str:
        # CSV replay mode does not require a screenshot and is the resilient fallback path.
        try:
            print(f"[UIRenderer] {reason}; falling back to CSV inference mode.")
            if hasattr(self.analyzer, "_analyze_with_csv_random"):
                return self.analyzer._analyze_with_csv_random(layout)

            prev_mode = getattr(self.analyzer, "mode", None)
            try:
                self.analyzer.mode = "csv"
                return self.analyzer.analyze("", layout)
            finally:
                if prev_mode is not None:
                    self.analyzer.mode = prev_mode
        except Exception as e:
            print(f"[UIRenderer] CSV inference fallback failed: {e}")
            return "UI rendering failed - could not capture screenshot."

    def _is_valid_analysis_json(self, text: str) -> bool:
        try:
            parsed = json.loads(str(text or ""))
        except Exception:
            return False

        if not isinstance(parsed, dict):
            return False

        required = {"Kiosk 1", "Kiosk 2", "Kiosk 3"}
        return required.issubset(set(parsed.keys()))

    def get_ui_description(self, layout: Dict[str, Any]) -> str:
        screenshot_path = self.render_and_capture(layout)
        if not screenshot_path:
            return self._fallback_to_csv_inference(layout, "Screenshot capture failed")

        analyzed = self.analyze_screenshot(screenshot_path, layout=layout)
        if not self._is_valid_analysis_json(analyzed):
            return self._fallback_to_csv_inference(layout, "Analysis unavailable")

        return analyzed
