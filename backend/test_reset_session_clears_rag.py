"""
Unit test for D053: AIAssistant.reset_session() must clear the RAG store.

D018/D023 found the RAG store (rag.py) persists across every participant's
session because reset_session() never called RAGStore.clear() - confirmed to
have contaminated all 38 sessions that used the AI assistant. D053 fixed this.

Uses a lightweight stub in place of a real RAGStore (which requires
sentence-transformers + faiss, not installed in this environment) so this test
exercises exactly the integration logic that was fixed - "does reset_session()
call rag_store.clear()" - without needing those heavier dependencies or
touching the real backend/rag_index/ on disk.
"""
import unittest

from ai_assistant import AIAssistant


class FakeRAGStore:
    """Stand-in for rag.RAGStore - tracks whether/how many times clear() was
    called, without needing sentence-transformers/faiss or touching disk."""

    def __init__(self):
        self.clear_calls = 0

    def clear(self):
        self.clear_calls += 1


class ResetSessionClearsRAGTest(unittest.TestCase):
    def setUp(self):
        # rag_enabled=False avoids constructing a real RAGStore (which would
        # need sentence-transformers/faiss) - the fake is attached afterward.
        self.ai = AIAssistant(rag_enabled=False, incident_mode=True)
        self.fake_store = FakeRAGStore()
        self.ai.rag_store = self.fake_store

    def test_reset_session_calls_rag_store_clear(self):
        self.ai.reset_session()
        self.assertEqual(
            self.fake_store.clear_calls, 1,
            "reset_session() must call rag_store.clear() exactly once (D053 fix for D018/D023's contamination finding)",
        )

    def test_reset_session_still_resets_other_session_state(self):
        # Guard against the fix accidentally removing reset_session()'s
        # pre-existing behaviour (D017's original scope).
        self.ai.charging_context = [{"trial": 1, "kiosk": "Kiosk 1"}]
        self.ai.screenshot_history = {"1": "some context"}
        self.ai.current_screenshot_context = "x"
        self.ai.current_screenshot_station = "1"

        self.ai.reset_session()

        self.assertEqual(self.ai.charging_context, [])
        self.assertEqual(self.ai.screenshot_history, {})
        self.assertIsNone(self.ai.current_screenshot_context)
        self.assertIsNone(self.ai.current_screenshot_station)

    def test_reset_session_tolerates_missing_rag_store(self):
        # rag_store can legitimately be None (RAG disabled, or init failed) -
        # reset_session() must not raise in that case.
        self.ai.rag_store = None
        try:
            self.ai.reset_session()
        except Exception as e:
            self.fail(f"reset_session() raised with rag_store=None: {e}")

    def test_reset_session_does_not_raise_if_clear_fails(self):
        # A RAGStore.clear() failure (e.g. a disk error) must be caught and
        # logged, not allowed to crash session reset for the whole game.
        class BrokenRAGStore:
            def clear(self):
                raise OSError("simulated disk failure")

        self.ai.rag_store = BrokenRAGStore()
        try:
            self.ai.reset_session()
        except Exception as e:
            self.fail(f"reset_session() raised when rag_store.clear() failed: {e}")


if __name__ == "__main__":
    unittest.main()
