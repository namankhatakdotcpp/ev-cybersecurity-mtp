"""
receive_ui.py
Simple BeamNG Python backend that listens for JSON messages sent from the UI
app via the `evProjectBridge` GE Lua extension and prints them.

Usage:
  pip install beamngpy
  python receive_ui.py --home "D:\\BeamNG\\BeamNG.tech.v0.38.3.0"

The script polls the GE extension and prints any new messages. It's intentionally

EV Charging Game - BeamNG backend (refactored)

This file contains `EVBackend`, a class that encapsulates the previous
procedural logic. It starts BeamNG, spawns a vehicle, runs an odometer loop and
handles parking-hold behavior in response to UI JSON messages sent via the
`evProjectBridge` GE extension.

Usage:
  pip install beamngpy
  python receive_ui.py --home "D:\\BeamNG\\BeamNG.tech.v0.38.3.0"
"""

import time
import json
import math
import argparse
import threading
import csv
from typing import Optional, Tuple
import random
from datetime import datetime
from pathlib import Path

from beamngpy import BeamNGpy, Vehicle
from ai_assistant import AIAssistant
from audio_direction import play_input
from tts_player import AssistantSpeechPlayer


class EVBackend:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 25252,
        home: Optional[str] = None,
        use_vulkan: bool = True,
        rag_enabled: bool = True,
        interaction_log_dir: Optional[str] = None,
        experiment_config: Optional[dict] = None,
    ):
        # Pass gfx preference into BeamNGpy constructor so the launched
        # BeamNG.tech process receives the correct `-gfx` switch.
        gfx = 'vk' if use_vulkan else None
        self.bng = BeamNGpy(host, port, home=home, gfx=gfx)
        self.vehicle: Optional[Vehicle] = None

        # Station-layout generation config (mirrors frontend rules)
        self.config = {
            'starting_points': 300,
            'initial_charge_min': 20,
            'initial_charge_max': 40,
            'assistant_help_cost': 2,
            'enable_coupon_discount': True,
            'incident_mode': False, #True -> Cyber Attack mode; False -> Anomaly mode
            'deepfake_attack_probability': 0.8,
            'real_attack_probability': 0.2,
            'discount_coupon_chance': 0.2,
            'image_selection_threshold': 0.5,
            'coupon_code_image_prob': 0.8,
            'cyber_attack_no_charge_probability': 0.2,
            'cyber_attack_reduced_charge_probability': 0.8,
        }
        if isinstance(experiment_config, dict):
            for key, value in experiment_config.items():
                if key in self.config:
                    self.config[key] = value

        self.interaction_log_dir = interaction_log_dir
        self.charge_multiplier = 0.01
        self.current_points: float = float(self.config['starting_points'])
        self.current_charge: Optional[float] = None
        self.drive_leg_start_odometer: Optional[float] = None
        self.last_charge_applied_seq: Optional[int] = None
        self.last_charge_event_key: Optional[tuple] = None
        self.last_charge_event_time: Optional[float] = None
        self.out_of_fuel_handled = False
        self.last_battery_push_time = 0.0
        self.last_station_layout: Optional[dict] = None
        self.last_station_number: Optional[int] = None
        self.flowgraph_finished = False
        self.last_flowgraph_message: str = ''
        self.last_flowgraph_station: Optional[int] = None
        self.shutdown_requested = False
        self.final_points_saved = False
        self.session_output_dir: Optional[Path] = Path(interaction_log_dir) if interaction_log_dir else None
        if self.session_output_dir is not None:
            self.session_output_dir.mkdir(parents=True, exist_ok=True)
        self.deepfake_images = [
            'deepfake1.png', 'deepfake2.png', 'deepfake6.png',
            'deepfake7.png', 'deepfake8.png', 'deepfake9.png'
        ]
        self.real_images = [
            'real4.png', 'real6.png', 'real7.png',
            'real8.png', 'real9.png'
        ]

        # UI thread
        self.ui_stop = threading.Event()
        self.ui_thread: Optional[threading.Thread] = None

        # Odometer worker thread
        self.odo_stop = threading.Event()
        self.odo_thread: Optional[threading.Thread] = None

        # Odometer and motion filtering
        self.odometer_total = 0.0
        self.prev_pos: Optional[Tuple[float, float, float]] = None
        self.teleport_threshold = 50.0

        # Stop logic
        self.stopping_steps = 5

        # AI assistant (screenshot/VLM/LLM/RAG; no gaze-tracking)
        self.ai = AIAssistant(rag_enabled=rag_enabled, incident_mode=self._get_incident_mode())
        self.ai_analysis_lock = threading.Lock()
        self.ai_analysis_in_progress = False
        self.assistant_speech = AssistantSpeechPlayer(delay_seconds=0.4)

        # Per-run interaction log
        self.log_lock = threading.Lock()
        self.log_file = None
        self.log_writer = None
        self.log_path: Optional[Path] = None
        self._init_interaction_log()

    def _init_interaction_log(self) -> None:
        if self.interaction_log_dir:
            logs_dir = Path(self.interaction_log_dir)
        else:
            logs_dir = Path(__file__).resolve().parent / 'interaction_logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        run_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_path = logs_dir / f'interactions_{run_stamp}.csv'
        self.log_file = open(self.log_path, 'w', newline='', encoding='utf-8')
        self.log_writer = csv.writer(self.log_file)
        self.log_writer.writerow([
            'timestamp_iso',
            'timestamp_unix_ms',
            'direction',
            'channel',
            'route',
            'message',
            'page',
            'trial',
            'seq',
            'payload_json',
            'raw_message',
        ])
        self.log_file.flush()
        print(f'[backend] Interaction log file: {self.log_path}')

    def _log_interaction(
        self,
        direction: str,
        channel: str,
        payload: Optional[dict] = None,
        raw_message: str = '',
    ) -> None:
        if not self.log_writer or not self.log_file:
            return

        now = datetime.now()
        now_iso = now.isoformat(timespec='milliseconds')
        now_ms = int(now.timestamp() * 1000)

        route = ''
        message = ''
        page = ''
        trial = ''
        seq = ''
        payload_json = ''

        if isinstance(payload, dict):
            route = str(payload.get('route', ''))
            message = str(payload.get('Message', payload.get('message', '')))
            page = str(payload.get('page', ''))
            trial = str(payload.get('trial', payload.get('Station', '')))
            seq = str(payload.get('seq', ''))
            try:
                payload_json = json.dumps(payload, ensure_ascii=True)
            except Exception:
                payload_json = ''

        with self.log_lock:
            self.log_writer.writerow([
                now_iso,
                now_ms,
                direction,
                channel,
                route,
                message,
                page,
                trial,
                seq,
                payload_json,
                raw_message,
            ])
            self.log_file.flush()

    # ------------------------ Messaging helpers ------------------------
    def _send_to_ui(self, payload: dict) -> None:
        sent = False
        try:
            text = json.dumps(payload)
            escaped = text.replace('\\', '\\\\').replace("'", "\\'")
            self.bng.control.queue_lua_command("extensions.evProjectBridge.sendToUI('" + escaped + "')")
            sent = True
        except Exception as e:
            print('[backend] Failed to send message to UI via evProjectBridge.sendToUI:', e)
            # Fallback: dispatch directly through the UI event bus.
            try:
                safe_text = text.replace(']]', '] ]')
                self.bng.control.queue_lua_command(
                    "guihooks.trigger('evProjectMessage', {message=[[" + safe_text + "]]})"
                )
                print('[backend] Sent message to UI via guihooks fallback')
                sent = True
            except Exception as fallback_err:
                print('[backend] Failed to send message to UI via guihooks fallback:', fallback_err)
        finally:
            if sent:
                self._log_interaction(direction='outgoing', channel='ui', payload=payload)
                self._speak_assistant_reply_if_needed(payload)

    def _speak_assistant_reply_if_needed(self, payload: dict) -> None:
        try:
            route = str(payload.get('route', '')).strip().lower()
            message = str(payload.get('Message', payload.get('message', ''))).strip().lower()
            if route != 'ai' or message != 'assistantreply':
                return

            reply_text = str(payload.get('reply') or '').strip()
            if not reply_text:
                return

            self.assistant_speech.speak_async(reply_text)
        except Exception as e:
            print('[backend] Failed to queue assistant TTS:', e)

    def _sanitize_assistant_reply_text(self, text: str) -> str:
        # Frontend and TTS do not render markdown; strip common bold markers.
        cleaned = str(text or '')
        cleaned = cleaned.replace('**', '')
        cleaned = cleaned.replace('__', '')
        return cleaned.strip()

    def _send_to_flowgraph(self, payload: dict) -> None:
        try:
            text = json.dumps(payload)
            escaped = text.replace('\\', '\\\\').replace("'", "\\'")
            self.bng.control.queue_lua_command("extensions.evProjectBridge.sendToFlowgraph('" + escaped + "')")
            print('[backend] Sent message to flowgraph:', text)
            self._log_interaction(direction='outgoing', channel='flowgraph', payload=payload)
        except Exception as e:
            print('[backend] Failed to send message to flowgraph:', e)

    def _send_to_battery_ui(self, payload: dict) -> None:
        try:
            text = json.dumps(payload)
            escaped = text.replace('\\', '\\\\').replace("'", "\\'")
            self.bng.control.queue_lua_command("extensions.evProjectBridge.sendBatteryToUI('" + escaped + "')")
        except Exception as e:
            print('[backend] Failed to send message to Battery UI:', e)

    def _publish_charge_state(self, force: bool = False) -> None:
        if self.current_charge is None:
            return
        now = time.time()
        if not force and (now - self.last_battery_push_time) < 0.5:
            return
        payload = {
            'route': 'Battery',
            'Message': 'ChargeUpdate',
            'charge': max(0.0, min(100.0, float(self.current_charge))),
            'odometer': float(self.odometer_total),
            'timestamp': now,
        }
        self._send_to_battery_ui(payload)
        self.last_battery_push_time = now

    def _analyze_station_layout_async(self, layout: dict) -> None:
        def _worker() -> None:
            with self.ai_analysis_lock:
                self.ai_analysis_in_progress = True
            try:
                description = self.ai.on_new_station(layout)
                self._send_to_ui({
                    'route': 'AI',
                    'Message': 'ScreenshotAnalyzed',
                    'Station': layout.get('Station'),
                    'description': description,
                })
            except Exception as e:
                print('[AI Assistant] Station analysis failed:', e)
            finally:
                with self.ai_analysis_lock:
                    self.ai_analysis_in_progress = False

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _ensure_ai_context_for_station(self, trial: int, timeout_seconds: float = 2.5) -> None:
        deadline = time.time() + max(0.0, timeout_seconds)

        while time.time() < deadline:
            if self.ai.has_verified_screenshot_context(trial):
                return

            with self.ai_analysis_lock:
                in_progress = self.ai_analysis_in_progress
            if not in_progress:
                break

            time.sleep(0.1)

        if self.ai.has_verified_screenshot_context(trial):
            return

        layout = self.last_station_layout
        if not isinstance(layout, dict):
            return

        try:
            layout_trial = int(layout.get('Station')) if layout.get('Station') is not None else None
        except Exception:
            layout_trial = None

        if layout_trial != trial:
            return

        try:
            print(f'[AI Assistant] Missing context for station {trial}; running synchronous station analysis recovery')
            self.ai.ensure_station_context(trial, layout=layout)
        except Exception as e:
            print('[AI Assistant] Synchronous station context recovery failed:', e)

    def _generate_station_layout(self, station_number: int) -> dict:
        try:
            self.ai.set_incident_mode(self._get_incident_mode())
        except Exception:
            pass

        if self.current_charge is None:
            self.current_charge = float(random.randint(self.config['initial_charge_min'], self.config['initial_charge_max']))

        num_occupied = 1 if random.random() < 0.5 else 0
        occupied_indices = random.sample(range(3), num_occupied) if num_occupied > 0 else []
        image_prob = self.config['coupon_code_image_prob'] > random.random()

        stations = []
        for i in range(3):
            is_occupied = i in occupied_indices
            station = {
                'id': i + 1,
                'name': f'Kiosk {i + 1}',
                'status': 'Occupied' if is_occupied else 'Available',
                'image': None,
                'attack': None,
                'cyber_attack_mode': None,
                'discount_coupon': False,
                'coupon_display_state': 'occupied',
                'mobile_upi': '',
                'charge_amount': ''
            }

            if not is_occupied:
                image_selection = random.random()
                attack_determination = random.random()
                discount_chance = random.random()

                if image_selection < self.config['image_selection_threshold'] and self.deepfake_images:
                    station['image'] = random.choice(self.deepfake_images)
                    station['attack'] = 'Cyber Attack' if attack_determination < self.config['deepfake_attack_probability'] else 'Safe'
                elif self.real_images:
                    station['image'] = random.choice(self.real_images)
                    station['attack'] = 'Cyber Attack' if attack_determination < self.config['real_attack_probability'] else 'Safe'
                else:
                    station['attack'] = 'Safe'

                if station['attack'] == 'Cyber Attack':
                    no_charge_prob = float(self.config.get('cyber_attack_no_charge_probability', 0.2))
                    reduced_prob = float(self.config.get('cyber_attack_reduced_charge_probability', 0.8))
                    total_prob = no_charge_prob + reduced_prob

                    if total_prob <= 0:
                        no_charge_prob = 0.2
                        reduced_prob = 0.8
                        total_prob = 1.0

                    no_charge_threshold = no_charge_prob / total_prob
                    station['cyber_attack_mode'] = 'blocked' if random.random() < no_charge_threshold else 'reduced'

                station['discount_coupon'] = discount_chance < self.config['discount_coupon_chance']
                station['coupon_display_state'] = 'coupon_image' if (image_prob and station['image']) else 'no_coupon'

            stations.append(station)

        return {
            'route': 'StationLayout',
            'Message': 'StationGenerated',
            'Station': station_number,
            'page': 'station',
            'charge': int(max(0.0, round(self.current_charge))),
            'points': int(max(0, round(self.current_points))),
            'assistant_help_cost': int(max(0, round(float(self.config.get('assistant_help_cost', 0) or 0)))),
            'enable_coupon_discount': bool(self.config.get('enable_coupon_discount', True)),
            'incident_mode': self._get_incident_mode(),
            'imageProb': image_prob,
            'stations': stations
        }

    def _get_incident_mode(self) -> bool:
        mode = self.config.get('incident_mode', True)

        if isinstance(mode, bool):
            return mode

        if isinstance(mode, (int, float)):
            return bool(mode)

        text = str(mode).strip().lower()
        if text in ('cyberattack', 'cyber attack', 'true', '1', 'yes', 'on'):
            return True
        if text in ('anomaly', 'false', '0', 'no', 'off'):
            return False
        return True

    def _sync_station_layout_state(self, layout: Optional[dict], station_number: Optional[int] = None) -> Optional[dict]:
        if not isinstance(layout, dict):
            return layout

        if station_number is not None:
            layout['Station'] = station_number
        elif self.last_station_number is not None:
            layout['Station'] = self.last_station_number

        layout['page'] = 'station'
        layout['route'] = 'StationLayout'
        layout['Message'] = 'StationGenerated'
        layout['incident_mode'] = self._get_incident_mode()
        layout['enable_coupon_discount'] = bool(self.config.get('enable_coupon_discount', True))
        layout['assistant_help_cost'] = int(max(0, round(float(self.config.get('assistant_help_cost', 0) or 0))))
        if self.current_charge is not None:
            layout['charge'] = int(max(0.0, round(self.current_charge)))
        layout['points'] = int(max(0, round(self.current_points)))
        return layout

    def _apply_ui_charge(self, obj: dict, page: str) -> bool:
        if self.current_charge is None:
            self.current_charge = float(random.randint(self.config['initial_charge_min'], self.config['initial_charge_max']))

        try:
            seq = obj.get('seq')
            seq_num = int(seq) if seq is not None else None
        except Exception:
            seq_num = None

        try:
            requested_amount = float(obj.get('charge_amount', 0) or 0)
        except Exception:
            requested_amount = 0.0

        try:
            trial_num = int(obj.get('trial')) if obj.get('trial') is not None else None
        except Exception:
            trial_num = None

        try:
            kiosk_num = int(obj.get('kiosk_used')) if obj.get('kiosk_used') is not None else None
        except Exception:
            kiosk_num = None

        event_key = (trial_num, kiosk_num, requested_amount)

        if seq_num is not None and self.last_charge_applied_seq == seq_num:
            return False
        if self.last_charge_event_key == event_key:
            print(
                f"[charge] Duplicate charge event ignored for page={page}, trial={trial_num}, kiosk={kiosk_num}, amount={requested_amount:.2f}"
            )
            return False
        now = time.time()

        effective_amount = max(0.0, requested_amount)
        before = self.current_charge
        self.current_charge = min(100.0, self.current_charge + effective_amount)
        if self.current_charge > 0.0:
            self.out_of_fuel_handled = False

        if seq_num is not None:
            self.last_charge_applied_seq = seq_num
        self.last_charge_event_key = event_key
        self.last_charge_event_time = now

        self._publish_charge_state(force=True)

        print(
            f"[charge] Charging applied from page={page}: requested={requested_amount:.2f}, "
            f"effective={effective_amount:.2f}, before={before:.2f}, after={self.current_charge:.2f}"
        )
        return True

    def _build_finished_payload(self) -> dict:
        payload = {
            'route': 'GameState',
            'Message': 'Finished',
            'page': 'end_game',
            'points': int(max(0, round(self.current_points))),
        }
        if self.current_charge is not None:
            payload['charge'] = int(max(0.0, round(self.current_charge)))
        if self.last_station_number is not None:
            payload['Station'] = self.last_station_number
        return payload

    def _save_final_points_snapshot(self, reason: str) -> None:
        if self.final_points_saved:
            return
        if self.session_output_dir is None:
            return

        payload = {
            'saved_at_iso': datetime.now().isoformat(timespec='seconds'),
            'reason': reason,
            'points': int(max(0, round(self.current_points))),
            'charge': int(max(0.0, round(self.current_charge or 0.0))),
            'station': self.last_station_number,
            'flowgraph_finished': bool(self.flowgraph_finished),
        }

        out_path = self.session_output_dir / 'final_points.json'
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=True)
            self.final_points_saved = True
            print(f'[backend] Final points snapshot saved: {out_path}')
        except Exception as e:
            print('[backend] Failed to save final points snapshot:', e)

    def _handle_incoming_json(self, obj: dict) -> None:
        route = str(obj.get('route', '')).strip().lower()

        if route == 'flowgraph':
            message = str(obj.get('Message', obj.get('message', ''))).strip().lower()
            self.last_flowgraph_message = message
            try:
                self.last_flowgraph_station = int(obj.get('Station')) if obj.get('Station') is not None else None
            except Exception:
                self.last_flowgraph_station = None
            if message == 'audiotrigger':
                try:
                    station_number = int(obj.get('Station', 0))
                except Exception:
                    station_number = 0
                print(f'[backend] AudioTrigger received: Station={station_number}')
                try:
                    play_input(station_number, wait=False)
                except Exception as e:
                    print('[backend] Audio trigger failed:', e)
                return
            if message == 'started':
                self._on_flowgraph_started(obj)
                return
            if message == 'finished' or (self.last_flowgraph_station is not None and self.last_flowgraph_station < 0):
                self.flowgraph_finished = True
                self.last_station_layout = None
                print('[backend] Flowgraph finished received; subsequent loadout requests will transition to end game')
                self._send_to_ui(self._build_finished_payload())
                return
            if message == 'reached':
                if self.flowgraph_finished:
                    print('[backend] Ignoring reached event because flowgraph already finished')
                    return
                if self.current_charge is None:
                    self.current_charge = float(random.randint(self.config['initial_charge_min'], self.config['initial_charge_max']))
                    self._publish_charge_state(force=True)

                if self.drive_leg_start_odometer is not None:
                    leg_distance = max(0.0, self.odometer_total - self.drive_leg_start_odometer)
                    discharge = leg_distance * self.charge_multiplier
                    print(
                        f"[charge] Driving leg distance={leg_distance:.2f} m, "
                        f"estimated_discharge={discharge:.2f}, current_charge={self.current_charge:.2f}"
                    )
                    self.drive_leg_start_odometer = None

                try:
                    station_number = int(obj.get('Station', 1))
                except Exception:
                    station_number = 1

                if self.last_station_layout is not None and self.last_station_number == station_number:
                    print(f'[backend] Duplicate reached event for station {station_number}; reusing existing layout')
                    synced = self._sync_station_layout_state(self.last_station_layout, station_number=station_number)
                    self._send_to_ui(synced)
                else:
                    layout = self._generate_station_layout(station_number)
                    self.last_station_layout = layout
                    self.last_station_number = station_number
                    self._sync_station_layout_state(self.last_station_layout, station_number=station_number)
                    print(f'[backend] Flowgraph reached station {station_number}, sending generated layout to UI')
                    self._send_to_ui(layout)
                    self._analyze_station_layout_async(layout)
            return

        if route == 'ui':
            page = str(obj.get('page', '')).strip().lower()
            if page in ('charging', 'disabled_charging'):
                applied = self._apply_ui_charge(obj, page)
                try:
                    ui_points = obj.get('points')
                    if ui_points is not None:
                        self.current_points = max(0.0, float(ui_points))
                except Exception:
                    pass

                if applied:
                    try:
                        self.ai.record_charging_event(
                            trial=int(obj.get('trial') or 0),
                            kiosk_used=int(obj.get('kiosk_used') or 0),
                            kiosk_attack=str(obj.get('kiosk_attack') or 'Safe'),
                            charge_amount=float(obj.get('charge_amount') or 0),
                            points_after=float(self.current_points),
                            ending_charge=float(self.current_charge or 0),
                        )
                    except Exception as e:
                        print('[AI Assistant] Failed to record charging event:', e)
                return

            if page == 'driving':
                self.drive_leg_start_odometer = self.odometer_total

                seq = obj.get('seq')
                payload = {
                    'route': 'Python',
                    'Message': 'DrivingPageReached',
                    'Station': obj.get('trial'),
                    'seq': seq,
                }
                self._send_to_flowgraph(payload)
                return

            if page == 'request_resend':
                if self.flowgraph_finished or self.last_flowgraph_message == 'finished' or (self.last_flowgraph_station is not None and self.last_flowgraph_station < 0):
                    self.flowgraph_finished = True
                    print('[backend] Flowgraph already finished; sending end-game transition to UI')
                    self._send_to_ui(self._build_finished_payload())
                    return
                if self.last_station_layout is not None:
                    print('[backend] Resending last station layout to UI')
                    synced = self._sync_station_layout_state(self.last_station_layout)
                    self._send_to_ui(synced)
                return

            if page in ('station', 'end_game'):
                # Sync points from UI
                try:
                    ui_points = obj.get('points')
                    if ui_points is not None:
                        self.current_points = max(0.0, float(ui_points))
                except Exception:
                    pass

            if page == 'end_game':
                self._save_final_points_snapshot('ui_end_game')
                self.shutdown_requested = True
                print('[backend] end_game page received; shutdown requested')
                return

            if page == 'assistant_chat':
                question = str(obj.get('message') or '').strip()
                assistant_cost = max(0.0, float(self.config.get('assistant_help_cost', 0) or 0))

                if not question:
                    self._send_to_ui({
                        'route': 'AI',
                        'Message': 'AssistantReply',
                        'reply': 'Please enter a question for the assistant.',
                        'assistant_cost': int(round(assistant_cost)),
                        'points': int(max(0, round(self.current_points))),
                    })
                    return

                if self.current_points < assistant_cost:
                    self._send_to_ui({
                        'route': 'AI',
                        'Message': 'AssistantReply',
                        'reply': f'Not enough points to use AI assistant. Required: {int(math.ceil(assistant_cost))}, available: {int(math.floor(self.current_points))}.',
                        'assistant_cost': int(round(assistant_cost)),
                        'points': int(max(0, round(self.current_points))),
                    })
                    return

                try:
                    self.current_points = max(0.0, self.current_points - assistant_cost)
                    trial_num = int(obj.get('trial') or self.last_station_number or 0)
                    self._ensure_ai_context_for_station(trial_num)

                    result = self.ai.ask(
                        message=question,
                        current_charge=float(self.current_charge or 0),
                        points=float(self.current_points),
                        trial=trial_num,
                    )
                    sanitized_reply = self._sanitize_assistant_reply_text(result.get('reply', ''))
                    self._send_to_ui({
                        'route': 'AI',
                        'Message': 'AssistantReply',
                        'reply': sanitized_reply,
                        'assistant_cost': int(round(assistant_cost)),
                        'points': int(max(0, round(self.current_points))),
                    })
                except Exception as e:
                    self._send_to_ui({
                        'route': 'AI',
                        'Message': 'AssistantReply',
                        'reply': f'Assistant error: {e}',
                        'assistant_cost': int(round(assistant_cost)),
                        'points': int(max(0, round(self.current_points))),
                    })
            return

    def _parse_ui_json(self, raw: str) -> Optional[dict]:
        try:
            msg = (raw or '').strip()
            if not msg:
                return None

            # Some bridge paths can wrap JSON in single/double quotes.
            if len(msg) >= 2 and ((msg[0] == "'" and msg[-1] == "'") or (msg[0] == '"' and msg[-1] == '"')):
                msg = msg[1:-1].strip()

            obj = json.loads(msg)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _attach_player_vehicle(self, retries: int = 10, delay: float = 0.3) -> bool:
        for attempt in range(retries):
            try:
                player = self.bng.vehicles.get_player_vehicle_id()
                player_id = player.get('id')
                player_vid = player.get('vid')

                if not player_vid:
                    raise RuntimeError('Player vid unavailable')

                current = self.bng.vehicles.get_current(include_config=False)
                vehicle = current.get(player_vid)
                if vehicle is None:
                    raise RuntimeError(f'Player vehicle {player_vid} not found in current vehicles')

                try:
                    vehicle.connect(self.bng)
                except Exception:
                    # If already connected or transient connection issue, continue checks below.
                    pass

                self.vehicle = vehicle
                self.prev_pos = None
                self.odometer_total = 0.0
                return True
            except Exception as e:
                if attempt == retries - 1:
                    print('[backend] Failed to attach to player vehicle:', e)
                    return False
                time.sleep(delay)

        return False

    def _start_odometer_worker(self) -> None:
        if self.odo_thread and self.odo_thread.is_alive():
            return
        self.odo_stop.clear()
        self.odo_thread = threading.Thread(target=self._odometer_worker, daemon=True)
        self.odo_thread.start()

    def _on_flowgraph_started(self, obj: dict) -> None:
        vehicle_id = obj.get('VehicleId')
        event_id = obj.get('EventId')
        print(f"[backend] Flowgraph Started received (VehicleId={vehicle_id}, EventId={event_id})")

        # Reset game-driving state on every new Started event.
        self.current_charge = float(random.randint(self.config['initial_charge_min'], self.config['initial_charge_max']))
        self.current_points = float(self.config['starting_points'])
        self.odometer_total = 0.0
        self.prev_pos = None
        self.drive_leg_start_odometer = None
        self.last_charge_applied_seq = None
        self.last_charge_event_key = None
        self.last_charge_event_time = None
        self.out_of_fuel_handled = False
        self.last_station_layout = None
        self.last_station_number = None
        self.flowgraph_finished = False
        self.ai.reset_session()
        print(f"[charge] Reset on Started: current_charge={self.current_charge:.2f}, points={self.current_points:.0f}")

        attached = self._attach_player_vehicle()
        if not attached:
            self._publish_charge_state(force=True)
            return

        self._publish_charge_state(force=True)

        self._start_odometer_worker()

    def _odometer_worker(self) -> None:
        while not self.odo_stop.is_set():
            try:
                if not self.vehicle:
                    time.sleep(0.2)
                    continue

                self.vehicle.poll_sensors()
                pos = self.vehicle.state.get('pos')
                if pos:
                    if self.prev_pos is None:
                        self.prev_pos = pos
                    else:
                        dx = pos[0] - self.prev_pos[0]
                        dy = pos[1] - self.prev_pos[1]
                        dz = pos[2] - self.prev_pos[2]
                        step = math.sqrt(dx * dx + dy * dy + dz * dz)
                        if step <= self.teleport_threshold:
                            self.odometer_total += step
                            if self.current_charge is not None:
                                discharge = step * self.charge_multiplier
                                self.current_charge = max(0.0, self.current_charge - discharge)
                                self._publish_charge_state(force=False)
                                if self.current_charge <= 0.0 and not self.out_of_fuel_handled:
                                    self.out_of_fuel_handled = True
                                    payload = {
                                        'route': 'Python',
                                        'Message': 'OutOfFuel',
                                    }
                                    self._send_to_flowgraph(payload)
                                    try:
                                        self._perform_gradual_stop()
                                    except Exception as stop_err:
                                        print('[backend] Error performing gradual stop on OutOfFuel:', stop_err)
                        self.prev_pos = pos
            except Exception as e:
                print('[backend] Error in background distance worker:', e)

            time.sleep(0.2)

    # ------------------------ Connection / scenario ------------------------
    def open(self, launch: bool = True) -> None:
        print('[backend] Connecting to BeamNG...')
        # BeamNGpy was constructed with the desired `gfx` option already
        # (via the constructor). Just call open normally.
        self.bng.open(launch=launch)
        time.sleep(0.5)
        # Ensure GE extension is loaded
        try:
            self.bng.control.queue_lua_command('extensions.load("evProjectBridge")')
            time.sleep(0.2)
        except Exception:
            pass

    # ------------------------ UI listener (thread) ------------------------
    def start_ui_listener(self) -> None:
        if self.ui_thread and self.ui_thread.is_alive():
            return
        self.ui_stop.clear()
        self.ui_thread = threading.Thread(target=self._ui_listener, args=(self.ui_stop,), daemon=True)
        self.ui_thread.start()

    def _ui_listener(self, stop_event: threading.Event) -> None:
        def _read_bridge_message() -> str:
            res = self.bng.control.queue_lua_command('return extensions.evProjectBridge.readFromUI()', response=True)
            return res if isinstance(res, str) else (str(res) if res is not None else '')

        last_msg = ''

        # Prime with any pre-existing buffered message so we don't process stale
        # JSON left over from before this backend started.
        try:
            primed = _read_bridge_message()
            if primed and primed != 'nil':
                last_msg = primed
                self._log_interaction(direction='incoming', channel='bridge', raw_message=primed)
                print('[UI thread] Primed existing bridge message; waiting for new UI/Flowgraph events')
        except Exception as e:
            print('[UI thread] Prime read failed:', e)

        while not stop_event.is_set():
            try:
                msg = _read_bridge_message()
                if msg and msg != 'nil' and msg != last_msg:
                    last_msg = msg
                    now_iso = datetime.now().isoformat(timespec='milliseconds')
                    print(f'\n[UI thread] Raw message @ {now_iso}:')
                    print(msg)
                    self._log_interaction(direction='incoming', channel='bridge', raw_message=msg)
                    try:
                        obj = self._parse_ui_json(msg)
                        if obj is None:
                            continue
                        obj['received_timestamp'] = now_iso
                        self._log_interaction(direction='incoming', channel='parsed_json', payload=obj, raw_message=msg)
                        print('\n[UI thread] Parsed JSON:')
                        print(json.dumps(obj, indent=2))
                        if isinstance(obj, dict):
                            try:
                                self._handle_incoming_json(obj)
                            except Exception as e:
                                print('[backend] Error handling incoming JSON:', e)
                        # Generic echo for debugging
                        echo = f"Received JSON ({len(msg)} chars)"
                        try:
                            try:
                                self.bng.control.queue_lua_command(f'extensions.evProjectBridge.sendToUI("{echo}")')
                            except Exception:
                                pass
                        except Exception:
                            pass
                    except Exception:
                        # not JSON; ignore
                        pass
            except Exception as e:
                print('[UI thread] Error reading UI extension:', e)
            time.sleep(0.2)

    # ------------------------ Respawn helpers ------------------------
    def set_respawn_to_current(self) -> Tuple[Optional[Tuple[float, float, float]], Optional[Tuple[float, float, float, float]]]:
        try:
            assert self.vehicle
            self.vehicle.poll_sensors()
            pos = self.vehicle.state.get('pos')
            rot = self.vehicle.state.get('rotation')
            if pos is None:
                raise RuntimeError('Vehicle position not available')
            rot_quat = tuple(rot) if rot is not None else None
            setattr(self.vehicle, '_respawn_point', tuple(pos))
            setattr(self.vehicle, '_respawn_rot', rot_quat)
            print(f"[respawn] Saved respawn point: pos={pos}, rot={rot_quat}")
            return (tuple(pos), rot_quat)
        except Exception as e:
            print('[respawn] Failed to save respawn point:', e)
            return (None, None)

    def _perform_gradual_stop(self) -> None:
        assert self.vehicle
        stopping_counter = 0
        while stopping_counter < self.stopping_steps:
            brake = min(1.0, (stopping_counter + 1) / float(self.stopping_steps))
            try:
                if stopping_counter <= 2:
                    # engage parking brake immediately to avoid reversing
                    self.vehicle.control(throttle=0.0, brake=brake, parkingbrake=0.0)
                else:
                    self.vehicle.control(throttle=0.0, brake=0.0, parkingbrake=1.0)
            except Exception as e:
                print('[backend] Error sending control to vehicle during stop:', e)
            stopping_counter += 1
            time.sleep(1.0)

        try:
            self.vehicle.control(throttle=0.0, brake=0.0, parkingbrake=1.0)
        except Exception:
            pass

        # update respawn
        try:
            self.set_respawn_to_current()
        except Exception as e:
            print('[respawn] Error setting respawn after stop:', e)

    # ------------------------ Shutdown ------------------------
    def stop(self) -> None:
        try:
            self.ui_stop.set()
        except Exception:
            pass
        try:
            if self.ui_thread:
                self.ui_thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.odo_stop.set()
        except Exception:
            pass
        try:
            if self.odo_thread:
                self.odo_thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.assistant_speech.stop()
        except Exception:
            pass
        try:
            self.bng.disconnect()
        except Exception:
            pass
        try:
            if self.log_file:
                self.log_file.close()
        except Exception:
            pass

def _load_experiment_config(path_str: Optional[str]) -> Optional[dict]:
    if not path_str:
        return None

    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f'Config JSON not found: {path}')

    with open(path, 'r', encoding='utf-8') as config_file:
        data = json.load(config_file)

    if isinstance(data, dict) and isinstance(data.get('game_config'), dict):
        return data['game_config']
    if isinstance(data, dict):
        return data
    raise ValueError('Config JSON must be an object')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=25252)
    parser.add_argument('--home', default=r'C:\\Users\\arjun\\Desktop\\BeamNG\\BeamNG.tech.v0.38.3.0', help='Path to BeamNG.tech home')
    parser.add_argument('--log-dir', default=None, help='Directory where per-run interaction CSV is saved')
    parser.add_argument('--config-json', default=None, help='Path to JSON file that can override game config')
    # Vulkan preference: default to True, allow --no-vulkan to disable
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--use-vulkan', dest='use_vulkan', action='store_true', help='Launch BeamNG with Vulkan (default)')
    group.add_argument('--no-vulkan', dest='use_vulkan', action='store_false', help='Do not use Vulkan')

    rag_group = parser.add_mutually_exclusive_group()
    rag_group.add_argument('--enable-rag', dest='rag_enabled', action='store_true', help='Enable RAG retrieval in AI assistant (default)')
    rag_group.add_argument('--disable-rag', dest='rag_enabled', action='store_false', help='Disable RAG retrieval in AI assistant')

    parser.set_defaults(use_vulkan=True)
    parser.set_defaults(rag_enabled=True)
    args = parser.parse_args()

    loaded_config = _load_experiment_config(args.config_json)

    backend = EVBackend(
        host=args.host,
        port=args.port,
        home=args.home,
        use_vulkan=args.use_vulkan,
        rag_enabled=args.rag_enabled,
        interaction_log_dir=args.log_dir,
        experiment_config=loaded_config,
    )
    try:
        backend.open(launch=True)
        backend.start_ui_listener()

        print('[backend] UI listener running. Press Ctrl+C to stop')
        while True:
            if backend.shutdown_requested:
                print('[backend] Graceful shutdown after end_game page')
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        print('\n[backend] Stopped by user')
    finally:
        backend.stop()
if __name__ == "__main__":
    main()
