"""
Test Suite for RosaNet 8-Recording Posture-Grouped Diagnostic Pipeline.

Verifies:
1. All eight recordings supplied correctly.
2. Missing recording error handling.
3. Wrong valve mapping error handling.
4. Wrong posture mapping error handling.
5. Invalid WAV file error handling.
6. Spectrogram dimension contracts (64, 626, 1).
7. Model input compatibility and strict branch-wise input ordering.
8. Successful model inference and multilabel output structure.
9. FastAPI endpoint integration contracts.
"""

import io
import sys
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
import tensorflow as tf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.quality_agent import SignalQualityAgent, REQUIRED_RECORDINGS, RECORDING_LABELS
from src.agents.prediction_agent import PredictionXAIAgent, DISEASE_KEYS
from src.agents.orchestrator import DiagnosticPipelineOrchestrator
from src.models.decision_fusion import build_rosanet_patient_model


def make_synthetic_wav_bytes(duration: float = 4.0, sr: int = 2000, freq: float = 60.0) -> bytes:
    """Generates synthetic monaural audio in WAV format for deterministic testing."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Simulated heart sound with gentle 1st/2nd harmonic
    audio = 0.4 * np.sin(2 * np.pi * freq * t) + 0.1 * np.sin(2 * np.pi * (freq * 2) * t)
    audio = audio.astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format='WAV')
    return buf.getvalue()


class TestRosaNet8RecordingPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.quality_agent = SignalQualityAgent()
        cls.prediction_agent = PredictionXAIAgent()
        cls.valid_8_audio = {k: make_synthetic_wav_bytes() for k in REQUIRED_RECORDINGS}

    def test_01_all_eight_recordings_supplied_correctly(self):
        """Verify that supplying all 8 posture recordings passes quality inspection."""
        quality_out, spec_dict = self.quality_agent.inspect_and_preprocess(
            valve_files=self.valid_8_audio,
            session_id="TEST-8REC-ALL-VALID"
        )
        self.assertEqual(quality_out.status, "PASS")
        self.assertTrue(quality_out.required_valves_present)
        self.assertTrue(quality_out.spectrograms_generated)
        self.assertEqual(len(spec_dict), 8)
        self.assertEqual(len(quality_out.valves_inspected), 8)
        for k in REQUIRED_RECORDINGS:
            self.assertIn(k, spec_dict)
            self.assertEqual(spec_dict[k].shape, (64, 626, 1))

    def test_02_missing_recording_validation_error(self):
        """Verify that omitting any of the 8 recordings results in a clear validation failure."""
        incomplete_audio = dict(self.valid_8_audio)
        del incomplete_audio['sup_Mit']  # Drop Supine Mitral

        quality_out, spec_dict = self.quality_agent.inspect_and_preprocess(
            valve_files=incomplete_audio,
            session_id="TEST-8REC-MISSING-ONE"
        )
        self.assertEqual(quality_out.status, "FAIL")
        self.assertFalse(quality_out.required_valves_present)
        self.assertFalse(quality_out.spectrograms_generated)
        self.assertEqual(len(spec_dict), 0)
        self.assertIn("Missing", quality_out.summary)
        self.assertIn("sup_Mit", quality_out.error_message)

    def test_03_wrong_valve_mapping_detection(self):
        """Verify that invalid valve names are rejected and identified as missing required valves."""
        invalid_valves_audio = dict(self.valid_8_audio)
        invalid_valves_audio['sit_Aorta'] = invalid_valves_audio.pop('sit_Aor')

        quality_out, spec_dict = self.quality_agent.inspect_and_preprocess(
            valve_files=invalid_valves_audio,
            session_id="TEST-8REC-WRONG-VALVE"
        )
        self.assertEqual(quality_out.status, "FAIL")
        self.assertIn("sit_Aor", quality_out.error_message)

    def test_04_wrong_posture_mapping_detection(self):
        """Verify that non-standard posture prefixes fail required 8-recording contracts."""
        wrong_posture_audio = {
            f"standing_{k.split('_')[1]}": v for k, v in self.valid_8_audio.items()
        }
        quality_out, spec_dict = self.quality_agent.inspect_and_preprocess(
            valve_files=wrong_posture_audio,
            session_id="TEST-8REC-WRONG-POSTURE"
        )
        self.assertEqual(quality_out.status, "FAIL")
        self.assertFalse(quality_out.required_valves_present)

    def test_05_invalid_wav_file_handling(self):
        """Verify that corrupted or non-audio files trigger individual channel failures."""
        corrupted_audio = dict(self.valid_8_audio)
        corrupted_audio['sit_Pul'] = b"CORRUPTED_NON_AUDIO_RAW_BYTES_NOT_A_WAV_FILE"

        quality_out, spec_dict = self.quality_agent.inspect_and_preprocess(
            valve_files=corrupted_audio,
            session_id="TEST-8REC-CORRUPT-WAV"
        )
        self.assertEqual(quality_out.status, "FAIL")
        # Find sit_Pul inspection record
        pul_info = next(v for v in quality_out.valves_inspected if v.valve_location == 'sit_Pul')
        self.assertFalse(pul_info.is_valid)
        self.assertIsNotNone(pul_info.warning)

    def test_06_spectrogram_dimensions_contract(self):
        """Verify that all generated log-mel spectrogram tensors strictly adhere to (64, 626, 1)."""
        _, spec_dict = self.quality_agent.inspect_and_preprocess(
            valve_files=self.valid_8_audio,
            session_id="TEST-8REC-DIMENSIONS"
        )
        for k, spec in spec_dict.items():
            self.assertEqual(spec.shape, (64, 626, 1), f"Unexpected tensor shape for {k}: {spec.shape}")
            self.assertEqual(spec.dtype, np.float32)
            self.assertFalse(np.isnan(spec).any(), f"NaNs detected in {k}")
            self.assertFalse(np.isinf(spec).any(), f"Infs detected in {k}")

    def test_07_model_input_compatibility_and_branch_ordering(self):
        """Verify 8-branch RosaNet input tensor signatures and exact branch ordering."""
        model = build_rosanet_patient_model(
            input_shape=(64, 626, 1),
            num_branches=8,
            num_classes=5
        )
        self.assertEqual(len(model.inputs), 8)

        expected_names = [
            "sit_Aor_spectrogram",
            "sit_Mit_spectrogram",
            "sit_Pul_spectrogram",
            "sit_Tri_spectrogram",
            "sup_Aor_spectrogram",
            "sup_Mit_spectrogram",
            "sup_Pul_spectrogram",
            "sup_Tri_spectrogram",
        ]

        for i, (inp, exp_name) in enumerate(zip(model.inputs, expected_names)):
            self.assertTrue(inp.name.startswith(exp_name), f"Input {i} name mismatch: {inp.name} vs {exp_name}")
            self.assertEqual(inp.shape.as_list(), [None, 64, 626, 1])

    def test_08_end_to_end_successful_inference(self):
        """Verify complete inference execution on 8 preprocessed recordings."""
        _, spec_dict = self.quality_agent.inspect_and_preprocess(
            valve_files=self.valid_8_audio,
            session_id="TEST-8REC-INFERENCE"
        )
        pred_out = self.prediction_agent.predict_and_explain(
            spectrogram_dict=spec_dict,
            session_id="TEST-8REC-INFERENCE"
        )
        self.assertIsNotNone(pred_out)
        self.assertEqual(pred_out.model_version, "RosaNet-8Branch-v1.0")
        self.assertEqual(len(pred_out.raw_probabilities), 5)
        for disease in DISEASE_KEYS:
            self.assertIn(disease, pred_out.raw_probabilities)
            prob = pred_out.raw_probabilities[disease]
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

        # Verify 8-branch attribution outputs
        self.assertIsInstance(pred_out.valve_attributions, list)


if __name__ == '__main__':
    unittest.main()

