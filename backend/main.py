"""
main.py
Browser-based intake launcher for EVChargingGame data collection.

Flow:
1) Starts a local web intake (intro/consent/demographics/instructions).
2) Stores intake data into a new session folder under ./raw_data.
3) Appends a quick-reference row to ./raw_data/sessions_reference.csv.
4) Launches receive_ui.py with session-specific log and config paths.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional


BACKEND_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BACKEND_DIR / "raw_data"
INTAKE_DIR = BACKEND_DIR / "intake_web"
REFERENCE_CSV = RAW_DATA_DIR / "sessions_reference.csv"


DEFAULT_SYSTEM_CONFIG: Dict[str, Any] = {
    "beamng": {
        "host": "localhost",
        "port": 25252,
        "home": r"C:\Users\arjun\Desktop\BeamNG\BeamNG.tech.v0.38.3.0",
        "use_vulkan": True,
        "rag_enabled": True,
    },
    "game_config": {
        "starting_points": 350,
        "initial_charge_min": 20,
        "initial_charge_max": 40,
        "enable_coupon_discount": True,
        "incident_mode": False,
        "deepfake_attack_probability": 0.8,
        "real_attack_probability": 0.2,
        "discount_coupon_chance": 0.2,
        "image_selection_threshold": 0.5,
        "coupon_code_image_prob": 0.8,
        "cyber_attack_no_charge_probability": 0.2,
        "cyber_attack_reduced_charge_probability": 0.8,
    },
}


class IntakeState:
    def __init__(self) -> None:
        self.done = threading.Event()
        self.error: Optional[str] = None
        self.session_dir: Optional[Path] = None
        self.system_config: Dict[str, Any] = json.loads(json.dumps(DEFAULT_SYSTEM_CONFIG))


def _safe_session_name(participant_id: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in participant_id.strip())
    clean = clean[:40] if clean else "anonymous"
    return f"session_{stamp}_{clean}"


def _create_session_dir(participant_id: str) -> Path:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    base = RAW_DATA_DIR / _safe_session_name(participant_id)
    session_dir = base
    suffix = 1
    while session_dir.exists():
        session_dir = RAW_DATA_DIR / f"{base.name}_{suffix}"
        suffix += 1
    session_dir.mkdir(parents=True, exist_ok=False)
    return session_dir


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=True)


def _append_reference_csv(
    session_dir: Path,
    consent_data: Dict[str, Any],
    demographics_data: Dict[str, Any],
    system_config: Dict[str, Any],
) -> None:
    REFERENCE_CSV.parent.mkdir(parents=True, exist_ok=True)
    exists = REFERENCE_CSV.exists()

    row = {
        "session_folder": session_dir.name,
        "created_at_iso": datetime.now().isoformat(timespec="seconds"),
        "participant_id": str(demographics_data.get("participant_id", "")),
        "age": str(demographics_data.get("age", "")),
        "gender": str(demographics_data.get("gender", "")),
        "consent_given": str(bool(consent_data.get("accepted", False))),
        "demographics_json": json.dumps(demographics_data, ensure_ascii=True),
        "system_config_json": json.dumps(system_config, ensure_ascii=True),
    }

    with open(REFERENCE_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "session_folder",
                "created_at_iso",
                "participant_id",
                "age",
                "gender",
                "consent_given",
                "demographics_json",
                "system_config_json",
            ],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _normalize_system_config(raw_config: Any) -> Dict[str, Any]:
    cfg: Dict[str, Any] = json.loads(json.dumps(DEFAULT_SYSTEM_CONFIG))

    if not isinstance(raw_config, dict):
        return cfg

    beamng = raw_config.get("beamng") if isinstance(raw_config.get("beamng"), dict) else {}
    game_config = raw_config.get("game_config") if isinstance(raw_config.get("game_config"), dict) else {}

    cfg["beamng"].update(beamng)
    cfg["game_config"].update(game_config)
    return cfg


def _make_handler(state: IntakeState):
    class IntakeHandler(SimpleHTTPRequestHandler):
        def copyfile(self, source, outputfile):
            try:
                super().copyfile(source, outputfile)
            except (BrokenPipeError, ConnectionResetError):
                # Remote client closed the connection while the file was being sent.
                # This is common when the browser stops loading or downloads are aborted.
                pass

        def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path != "/api/start-session":
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Invalid JSON"})
                return

            consent = body.get("consent") if isinstance(body.get("consent"), dict) else {}
            demographics = body.get("demographics") if isinstance(body.get("demographics"), dict) else {}
            # Intake page does not expose config editing. Always use backend defaults.
            system_config = _normalize_system_config(None)

            if not consent.get("accepted", False):
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Consent is required"})
                return

            participant_id = str(demographics.get("participant_id", "")).strip()
            if not participant_id:
                participant_id = "anonymous"

            try:
                session_dir = _create_session_dir(participant_id)
                _write_json(session_dir / "consent.json", consent)
                _write_json(session_dir / "demographics.json", demographics)
                _write_json(session_dir / "system_config.json", system_config)
                _append_reference_csv(session_dir, consent, demographics, system_config)

                state.session_dir = session_dir
                state.system_config = system_config
                state.done.set()

                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "session_folder": session_dir.name,
                    },
                )
            except Exception as exc:
                state.error = str(exc)
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": state.error})

    return IntakeHandler


def _run_intake_server(host: str, port: int, state: IntakeState) -> ThreadingHTTPServer:
    if not INTAKE_DIR.exists():
        raise FileNotFoundError(f"Intake web folder not found: {INTAKE_DIR}")

    handler_cls = _make_handler(state)
    rooted_handler = partial(handler_cls, directory=str(INTAKE_DIR))
    server = ThreadingHTTPServer((host, port), rooted_handler)
    return server


def _launch_receive_ui(session_dir: Path, system_config: Dict[str, Any]) -> int:
    beamng_cfg = system_config.get("beamng", {}) if isinstance(system_config, dict) else {}

    host = str(beamng_cfg.get("host", "localhost"))
    port = str(int(beamng_cfg.get("port", 25252)))

    home = str(beamng_cfg.get("home", DEFAULT_SYSTEM_CONFIG["beamng"]["home"]))

    use_vulkan = bool(beamng_cfg.get("use_vulkan", True))
    rag_enabled = bool(beamng_cfg.get("rag_enabled", True))

    config_json = session_dir / "system_config.json"

    cmd = [
        sys.executable,
        str(BACKEND_DIR / "receive_ui.py"),
        "--host",
        host,
        "--port",
        port,
        "--home",
        home,
        "--log-dir",
        str(session_dir),
        "--config-json",
        str(config_json),
    ]

    cmd.append("--use-vulkan" if use_vulkan else "--no-vulkan")
    cmd.append("--enable-rag" if rag_enabled else "--disable-rag")

    print(f"[main] Launching receive_ui.py for session folder: {session_dir}")
    return subprocess.call(cmd, cwd=str(BACKEND_DIR))


def main() -> None:
    parser = argparse.ArgumentParser(description="EVChargingGame intake + data collection launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Local host for intake web server")
    parser.add_argument("--port", type=int, default=8765, help="Local port for intake web server")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open intake page in browser")
    args = parser.parse_args()

    state = IntakeState()
    server = _run_intake_server(args.host, args.port, state)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    intake_url = f"http://{args.host}:{args.port}/index.html"
    print(f"[main] Intake server running at: {intake_url}")
    if not args.no_browser:
        webbrowser.open(intake_url, new=1)

    try:
        print("[main] Waiting for participant intake submission...")
        state.done.wait()
    except KeyboardInterrupt:
        print("\n[main] Stopped before intake submission.")
        return
    finally:
        server.shutdown()
        server.server_close()

    if state.error:
        raise RuntimeError(f"Intake failed: {state.error}")

    if not state.session_dir:
        raise RuntimeError("Intake did not produce a session folder")

    exit_code = _launch_receive_ui(state.session_dir, state.system_config)
    if exit_code != 0:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
