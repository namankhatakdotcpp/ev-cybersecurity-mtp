import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from typing import Optional

import sounddevice as sd
import soundfile as sf


class AssistantSpeechPlayer:
    """Background speech player for assistant replies.

    Uses Edge TTS only (free, no API key).
    """

    def __init__(self, delay_seconds: float = 0.0):
        self.delay_seconds = max(0.0, float(delay_seconds))
        self._queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._run, daemon=True)

        self._edge_voice = os.environ.get('EDGE_TTS_VOICE', 'en-IN-NeerjaNeural')
        self._edge_rate = os.environ.get('EDGE_TTS_RATE', '+30%')       
        self._edge_volume = os.environ.get('EDGE_TTS_VOLUME', '-40%')
        self._edge_failed = False

        self._worker.start()

    def speak_async(self, text: str) -> None:
        clean = self._sanitize_text(text)
        if not clean:
            return
        try:
            self._queue.put_nowait(clean)
        except Exception:
            pass

    def stop(self) -> None:
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        try:
            self._worker.join(timeout=1.0)
        except Exception:
            pass

    def _sanitize_text(self, text: str) -> str:
        clean = ' '.join(str(text or '').split())
        if not clean:
            return ''
        return clean[:900]

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if text is None:
                continue

            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds)

            if self._speak_with_edge_tts(text):
                continue
            print('[tts] Skipping playback: Edge TTS is unavailable')

    def _speak_with_edge_tts(self, text: str) -> bool:
        if self._edge_failed:
            return False

        tmp_file = None
        try:
            # Use module invocation so it works with the active Python env.
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                tmp_file = f.name

            cmd = [
                sys.executable,
                '-m',
                'edge_tts',
                '--voice',
                self._edge_voice,
                f'--rate={self._edge_rate}',
                f'--volume={self._edge_volume}',
                '--text',
                text,
                '--write-media',
                tmp_file,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                stderr = (result.stderr or '').strip()
                if 'No module named' in stderr:
                    print('[tts] edge-tts is not installed. Run: pip install edge-tts')
                    self._edge_failed = True
                else:
                    print(f'[tts] edge-tts synthesis failed: {stderr}')
                return False

            audio_data, sample_rate = sf.read(tmp_file, dtype='float32', always_2d=False)
            sd.play(audio_data, sample_rate)
            sd.wait()
            return True
        except Exception as e:
            print(f'[tts] Edge TTS playback failed: {e}')
            return False
        finally:
            if tmp_file:
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

