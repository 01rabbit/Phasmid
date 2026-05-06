import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.object_cue_policy_gate import CueFrameSignal, ObjectCuePolicyGate


class ObjectCuePolicyGateTests(unittest.TestCase):
    def test_no_signal_returns_idle(self):
        gate = ObjectCuePolicyGate()
        result = gate.evaluate([])
        self.assertEqual(result.sequence_state, "idle")
        self.assertFalse(result.accepted)

    def test_ambiguous_scene_rejected(self):
        gate = ObjectCuePolicyGate()
        result = gate.evaluate(
            [
                CueFrameSignal("detected"),
                CueFrameSignal("ambiguous"),
                CueFrameSignal("matched"),
            ]
        )
        self.assertEqual(result.sequence_state, "ambiguous")
        self.assertTrue(result.ambiguous)
        self.assertFalse(result.accepted)

    def test_no_object_scene_rejected(self):
        gate = ObjectCuePolicyGate()
        result = gate.evaluate([CueFrameSignal("none"), CueFrameSignal("none")])
        self.assertEqual(result.reason, "no_object")
        self.assertFalse(result.accepted)

    def test_stable_match_accepts(self):
        gate = ObjectCuePolicyGate(required_stable_frames=3)
        result = gate.evaluate(
            [
                CueFrameSignal("detected"),
                CueFrameSignal("matched"),
                CueFrameSignal("matched"),
                CueFrameSignal("matched"),
            ]
        )
        self.assertEqual(result.sequence_state, "matched")
        self.assertTrue(result.accepted)

    def test_sequence_timeout_rejected(self):
        gate = ObjectCuePolicyGate(sequence_timeout_frames=4)
        result = gate.evaluate(
            [
                CueFrameSignal("matched", relation_ok=True, token="a"),
                CueFrameSignal("matched", relation_ok=False, token="b"),
                CueFrameSignal("matched", relation_ok=False, token="b"),
                CueFrameSignal("matched", relation_ok=False, token="b"),
            ],
            expected_sequence=["a", "b"],
        )
        self.assertEqual(result.sequence_state, "timeout")
        self.assertFalse(result.accepted)

    def test_sequence_complete_accepts(self):
        gate = ObjectCuePolicyGate(sequence_timeout_frames=6)
        result = gate.evaluate(
            [
                CueFrameSignal("matched", relation_ok=True, token="a"),
                CueFrameSignal("matched", relation_ok=True, token="b"),
            ],
            expected_sequence=["a", "b"],
        )
        self.assertEqual(result.sequence_state, "matched")
        self.assertTrue(result.accepted)


if __name__ == "__main__":
    unittest.main()
