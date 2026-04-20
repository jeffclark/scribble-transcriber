"""Offline speaker diarization using MFCC clustering."""

import io
import logging

import numpy as np

logger = logging.getLogger(__name__)

MAX_SPEAKERS = 6
# Only accept a multi-speaker split when the silhouette score is meaningfully
# positive — scores below this typically reflect noise, not distinct voices.
MIN_SILHOUETTE = 0.3


def diarize_segments(audio_data: bytes, segments) -> list[str]:
    """
    Assign speaker labels to segments using MFCC + agglomerative clustering.

    Uses silhouette analysis to automatically determine the number of speakers
    (up to MAX_SPEAKERS) rather than a hand-tuned distance threshold.
    Returns list of "Speaker N" labels, one per segment, in order of first appearance.
    Works entirely offline with no external tokens required.
    """
    import librosa
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    audio, sr = librosa.load(io.BytesIO(audio_data), sr=16000, mono=True)

    embeddings: list[np.ndarray | None] = []
    valid_indices: list[int] = []

    for i, seg in enumerate(segments):
        start = int(seg.start * sr)
        end = int(seg.end * sr)
        chunk = audio[start:end]

        if len(chunk) < int(sr * 0.5):
            embeddings.append(None)
            continue

        mfcc = librosa.feature.mfcc(y=chunk, sr=sr, n_mfcc=13)
        feat = np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)])
        embeddings.append(feat)
        valid_indices.append(i)

    if len(valid_indices) < 2:
        return ["Speaker 1"] * len(segments)

    feats = np.array([embeddings[i] for i in valid_indices])
    feats = StandardScaler().fit_transform(feats)

    # Find the best k in [1, MAX_SPEAKERS] via silhouette score.
    # k=1 has no silhouette score (undefined), so we start from 2.
    # We keep k=1 as the fallback and only upgrade if a higher-k clustering
    # genuinely improves cohesion/separation.
    n_valid = len(valid_indices)
    best_k = 1
    best_score = -1.0

    for k in range(2, min(MAX_SPEAKERS + 1, n_valid)):
        labels_k = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(feats)
        score = silhouette_score(feats, labels_k)
        logger.debug(f"Silhouette k={k}: {score:.3f}")
        if score > best_score and score >= MIN_SILHOUETTE:
            best_score = score
            best_k = k

    logger.info(f"Diarization: selected {best_k} speaker(s) (silhouette={best_score:.3f})")

    if best_k == 1:
        labels = np.zeros(n_valid, dtype=int)
    else:
        labels = AgglomerativeClustering(n_clusters=best_k, linkage="ward").fit_predict(feats)

    result: list[str | None] = [None] * len(segments)
    speaker_map: dict[int, str] = {}
    next_id = 1
    for pos, idx in enumerate(valid_indices):
        cluster = int(labels[pos])
        if cluster not in speaker_map:
            speaker_map[cluster] = f"Speaker {next_id}"
            next_id += 1
        result[idx] = speaker_map[cluster]

    # Fill skipped short segments from preceding neighbour
    last = "Speaker 1"
    for i in range(len(result)):
        if result[i] is None:
            result[i] = last
        else:
            last = result[i]

    return result  # type: ignore[return-value]
