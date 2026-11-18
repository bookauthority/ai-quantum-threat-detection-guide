from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence

from .data import RecordSample, WindowSample


@dataclass
class UnsupervisedBaselineModel:
    """Per-record unsupervised anomaly detector using simple z-score.

    Uses a subset of benign-like training data to learn mean and std of each
    feature, then scores samples by squared Mahalanobis distance under a
    diagonal covariance approximation. Threshold is chosen as a quantile of
    training scores.
    """

    mean_qber: float = 0.0
    std_qber: float = 1.0
    mean_secret_key_rate: float = 0.0
    std_secret_key_rate: float = 1.0
    threshold: float = 0.0

    def fit(self, train_samples: Sequence[RecordSample]) -> None:
        benign = [s for s in train_samples if s.is_attack == 0]
        if not benign:
            benign = list(train_samples)

        def mean_std(values: List[float]) -> (float, float):
            m = sum(values) / float(len(values))
            var = sum((v - m) ** 2 for v in values) / float(len(values))
            return m, math.sqrt(var) if var > 1e-12 else 1.0

        qs = [s.qber for s in benign]
        ks = [s.secret_key_rate for s in benign]
        self.mean_qber, self.std_qber = mean_std(qs)
        self.mean_secret_key_rate, self.std_secret_key_rate = mean_std(ks)

        scores = [self.score_sample(s) for s in benign]
        scores_sorted = sorted(scores)
        # 95th percentile as threshold
        if scores_sorted:
            idx = int(0.95 * (len(scores_sorted) - 1))
            self.threshold = scores_sorted[idx]
        else:
            self.threshold = 0.0

    def score_sample(self, s: RecordSample) -> float:
        z_q = (s.qber - self.mean_qber) / self.std_qber
        z_k = (s.secret_key_rate - self.mean_secret_key_rate) / self.std_secret_key_rate
        return z_q * z_q + z_k * z_k

    def predict(self, samples: Sequence[RecordSample]) -> List[int]:
        preds: List[int] = []
        for s in samples:
            score = self.score_sample(s)
            preds.append(1 if score >= self.threshold else 0)
        return preds


@dataclass
class SupervisedBaselineModel:
    """Per-record supervised attack detector.

    Learns a 1D threshold on a hand-crafted attack score combining QBER and
    (negative) secret key rate.
    """

    threshold: float = 0.0

    def _score(self, s: RecordSample) -> float:
        return s.qber - 0.5 * s.secret_key_rate

    def fit(self, train_samples: Sequence[RecordSample]) -> None:
        pairs = [
            (self._score(s), s.is_attack) for s in train_samples
        ]
        pairs.sort(key=lambda p: p[0])
        best_thr = 0.0
        best_acc = -1.0
        # Candidate thresholds midway between sorted scores
        for i in range(len(pairs)):
            thr = pairs[i][0]
            tp = fp = tn = fn = 0
            for score, y in pairs:
                pred = 1 if score >= thr else 0
                if pred == 1 and y == 1:
                    tp += 1
                elif pred == 1 and y == 0:
                    fp += 1
                elif pred == 0 and y == 0:
                    tn += 1
                else:
                    fn += 1
            total = tp + fp + tn + fn
            if total == 0:
                continue
            acc = float(tp + tn) / float(total)
            if acc > best_acc:
                best_acc = acc
                best_thr = thr
        self.threshold = best_thr

    def predict(self, samples: Sequence[RecordSample]) -> List[int]:
        preds: List[int] = []
        for s in samples:
            score = self._score(s)
            preds.append(1 if score >= self.threshold else 0)
        return preds


@dataclass
class UnsupervisedTreatmentModel:
    """Window-level unsupervised anomaly detector on sequence-style features."""

    mean_qber: float = 0.0
    std_qber: float = 1.0
    mean_attack_fraction: float = 0.0
    std_attack_fraction: float = 1.0
    threshold: float = 0.0

    def fit(self, train_samples: Sequence[WindowSample]) -> None:
        benign = [s for s in train_samples if s.is_attack_window == 0]
        if not benign:
            benign = list(train_samples)

        def mean_std(values: List[float]) -> (float, float):
            m = sum(values) / float(len(values))
            var = sum((v - m) ** 2 for v in values) / float(len(values))
            return m, math.sqrt(var) if var > 1e-12 else 1.0

        qs = [s.mean_qber for s in benign]
        af = [s.attack_fraction for s in benign]
        self.mean_qber, self.std_qber = mean_std(qs)
        self.mean_attack_fraction, self.std_attack_fraction = mean_std(af)

        scores = [self.score_sample(s) for s in benign]
        scores_sorted = sorted(scores)
        if scores_sorted:
            idx = int(0.95 * (len(scores_sorted) - 1))
            self.threshold = scores_sorted[idx]
        else:
            self.threshold = 0.0

    def score_sample(self, s: WindowSample) -> float:
        z_q = (s.mean_qber - self.mean_qber) / self.std_qber
        z_a = (s.attack_fraction - self.mean_attack_fraction) / self.std_attack_fraction
        return z_q * z_q + z_a * z_a

    def predict(self, samples: Sequence[WindowSample]) -> List[int]:
        preds: List[int] = []
        for s in samples:
            score = self.score_sample(s)
            preds.append(1 if score >= self.threshold else 0)
        return preds


@dataclass
class SupervisedTreatmentModel:
    """Window-level supervised classifier on aggregated attack score."""

    threshold: float = 0.0

    def _score(self, s: WindowSample) -> float:
        return s.mean_qber + 0.5 * s.attack_fraction - 0.3 * s.mean_secret_key_rate

    def fit(self, train_samples: Sequence[WindowSample]) -> None:
        pairs = [(self._score(s), s.is_attack_window) for s in train_samples]
        pairs.sort(key=lambda p: p[0])
        best_thr = 0.0
        best_acc = -1.0
        for i in range(len(pairs)):
            thr = pairs[i][0]
            tp = fp = tn = fn = 0
            for score, y in pairs:
                pred = 1 if score >= thr else 0
                if pred == 1 and y == 1:
                    tp += 1
                elif pred == 1 and y == 0:
                    fp += 1
                elif pred == 0 and y == 0:
                    tn += 1
                else:
                    fn += 1
            total = tp + fp + tn + fn
            if total == 0:
                continue
            acc = float(tp + tn) / float(total)
            if acc > best_acc:
                best_acc = acc
                best_thr = thr
        self.threshold = best_thr

    def predict(self, samples: Sequence[WindowSample]) -> List[int]:
        preds: List[int] = []
        for s in samples:
            score = self._score(s)
            preds.append(1 if score >= self.threshold else 0)
        return preds
