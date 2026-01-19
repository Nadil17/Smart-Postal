import types

import numpy as np
import pytest
import soundfile as sf
import torch

from utils.voice_banking import BankingGradeVoiceProcessor


class _FakeFeatureExtractor:
    def __call__(self, chunk, sampling_rate, return_tensors, padding):
        # Minimal tensor payload compatible with HF audio models
        # Shape doesn't matter for our fake model.
        return {"input_values": torch.zeros((1, 16000), dtype=torch.float32)}


class _FakeModel:
    def __init__(self, logits):
        self._logits = torch.tensor([logits], dtype=torch.float32)

    def to(self, device):
        return self

    def eval(self):
        return self

    def __call__(self, **kwargs):
        return types.SimpleNamespace(logits=self._logits)


def _write_wav(tmp_path, seconds=3.0, sr=16000):
    t = np.linspace(0, seconds, int(seconds * sr), endpoint=False)
    # A simple "voice-like" tone + noise; content doesn't matter since model is mocked.
    y = 0.05 * np.sin(2 * np.pi * 220 * t) + 0.005 * np.random.randn(len(t))
    path = tmp_path / "sample.wav"
    sf.write(str(path), y.astype(np.float32), sr)
    return str(path)


@pytest.mark.parametrize(
    "logits, expected_is_human",
    [
        ([-2.0, 2.0], False),  # strongly fake
        ([2.0, -2.0], True),   # strongly real
    ],
)
def test_ai_detector_probability_mapping(tmp_path, monkeypatch, logits, expected_is_human):
    wav_path = _write_wav(tmp_path)

    vp = BankingGradeVoiceProcessor()

    def _fake_loader(self):
        self._ai_detector_error = None
        self._ai_model = _FakeModel(logits=logits)
        self._ai_feature_extractor = _FakeFeatureExtractor()

    monkeypatch.setattr(BankingGradeVoiceProcessor, "_ensure_ai_detector_loaded", _fake_loader)

    metrics = vp.detect_ai_synthetic_voice(wav_path, strict_mode=True)

    assert metrics.detection_method == "WAV2VEC2_DEEPFAKE_CLASSIFIER"
    assert metrics.is_human == expected_is_human
    assert 0.0 <= metrics.ai_probability <= 1.0


def test_ai_detector_unavailable_returns_neutral_probability(tmp_path, monkeypatch):
    wav_path = _write_wav(tmp_path)

    vp = BankingGradeVoiceProcessor()

    def _fake_loader(self):
        self._ai_detector_error = "boom"
        self._ai_model = None
        self._ai_feature_extractor = None

    monkeypatch.setattr(BankingGradeVoiceProcessor, "_ensure_ai_detector_loaded", _fake_loader)

    metrics = vp.detect_ai_synthetic_voice(wav_path, strict_mode=True)
    assert metrics.detection_method == "UNAVAILABLE"
    assert metrics.ai_probability == 0.50
    assert metrics.is_human is True
