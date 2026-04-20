"""Tests for speaker diarization service."""

import io
import wave

import numpy as np
import pytest

from src.services.diarization import diarize_segments


class FakeSeg:
    """Minimal segment stand-in with start/end attributes."""

    def __init__(self, start: float, end: float):
        self.start = start
        self.end = end


def _make_wav(samples: np.ndarray, sr: int = 16000) -> bytes:
    """Encode a float32 numpy array as a 16-bit mono WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def _voiced_chunk(freq: float, duration: float, sr: int = 16000) -> np.ndarray:
    """Synthetic voiced speech: fundamental + 4 harmonics with noise."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = sum(
        (1 / (k + 1)) * np.sin(2 * np.pi * freq * (k + 1) * t)
        for k in range(5)
    )
    signal += 0.05 * np.random.default_rng(42).standard_normal(len(t))
    return (signal / np.abs(signal).max() * 0.7).astype(np.float32)


def test_single_speaker_all_labelled_speaker_1():
    """Single speaker: every segment should be 'Speaker 1'."""
    sr = 16000
    audio = _voiced_chunk(120, 12, sr)
    wav = _make_wav(audio, sr)
    segs = [FakeSeg(0, 3), FakeSeg(3, 6), FakeSeg(6, 9)]
    labels = diarize_segments(wav, segs)
    assert labels == ["Speaker 1", "Speaker 1", "Speaker 1"]


def test_two_speakers_detected():
    """Two distinct voices (different fundamental frequencies) should cluster into 2 speakers."""
    sr = 16000
    seg_dur = 3.0
    # Speaker A: low-pitched (100 Hz fundamental)
    speaker_a = _voiced_chunk(100, seg_dur, sr)
    # Speaker B: high-pitched (300 Hz fundamental)
    speaker_b = _voiced_chunk(300, seg_dur, sr)

    audio = np.concatenate([
        speaker_a, speaker_a,  # segs 0, 1
        speaker_b, speaker_b,  # segs 2, 3
        speaker_a,             # seg 4
    ])
    wav = _make_wav(audio, sr)
    segs = [FakeSeg(i * seg_dur, (i + 1) * seg_dur) for i in range(5)]
    labels = diarize_segments(wav, segs)

    assert len(labels) == 5
    # Segments 0 and 1 should share a label; segments 2 and 3 should share a different label
    assert labels[0] == labels[1], "Speaker A segments should be the same speaker"
    assert labels[2] == labels[3], "Speaker B segments should be the same speaker"
    assert labels[0] != labels[2], "Speaker A and B should be different speakers"
    # Segment 4 is speaker A again
    assert labels[4] == labels[0], "Returning speaker A should match earlier label"


def test_short_segment_filled_from_neighbour():
    """Segments shorter than 0.5 s should inherit their neighbour's label."""
    sr = 16000
    audio = _voiced_chunk(150, 10, sr)
    wav = _make_wav(audio, sr)
    # Middle segment is only 0.2 s — too short for feature extraction
    segs = [FakeSeg(0, 3), FakeSeg(3, 3.2), FakeSeg(3.2, 6)]
    labels = diarize_segments(wav, segs)
    assert len(labels) == 3
    # All should be labelled (no None)
    assert all(isinstance(lbl, str) for lbl in labels)
    assert all(lbl.startswith("Speaker") for lbl in labels)


def test_returns_correct_length():
    """Output list length must equal input segment count."""
    sr = 16000
    audio = _voiced_chunk(200, 20, sr)
    wav = _make_wav(audio, sr)
    segs = [FakeSeg(i * 2, (i + 1) * 2) for i in range(10)]
    labels = diarize_segments(wav, segs)
    assert len(labels) == len(segs)


def test_zero_segments():
    """Empty segment list should return empty list without error."""
    sr = 16000
    audio = _voiced_chunk(200, 2, sr)
    wav = _make_wav(audio, sr)
    labels = diarize_segments(wav, [])
    assert labels == []


def test_single_segment():
    """Single segment should return ['Speaker 1'] without clustering."""
    sr = 16000
    audio = _voiced_chunk(200, 3, sr)
    wav = _make_wav(audio, sr)
    labels = diarize_segments(wav, [FakeSeg(0, 3)])
    assert labels == ["Speaker 1"]


def test_speaker_labels_ordered_by_first_appearance():
    """Speaker N labels should be assigned in order of first appearance."""
    sr = 16000
    seg_dur = 3.0
    speaker_a = _voiced_chunk(100, seg_dur, sr)
    speaker_b = _voiced_chunk(300, seg_dur, sr)
    audio = np.concatenate([speaker_a, speaker_b, speaker_a])
    wav = _make_wav(audio, sr)
    segs = [FakeSeg(i * seg_dur, (i + 1) * seg_dur) for i in range(3)]
    labels = diarize_segments(wav, segs)
    # First speaker seen should be "Speaker 1"
    assert labels[0] == "Speaker 1"
    # Second distinct speaker should be "Speaker 2"
    if labels[1] != labels[0]:
        assert labels[1] == "Speaker 2"
