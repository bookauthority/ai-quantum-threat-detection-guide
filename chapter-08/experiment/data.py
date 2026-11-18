from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple


RANDOM_SEED = 42


@dataclass
class RecordSample:
    qber: float
    sifted_key_rate: float
    secret_key_rate: float
    photon_count: float
    channel_loss_db: float
    is_attack: int  # 0 or 1


@dataclass
class WindowSample:
    mean_qber: float
    mean_secret_key_rate: float
    mean_photon_count: float
    channel_loss_db: float
    attack_fraction: float
    is_attack_window: int  # 0 or 1


def _seed_rng() -> None:
    random.seed(RANDOM_SEED)


def generate_per_record_dataset(
    n_train: int = 200,
    n_test: int = 200,
    attack_ratio_train: float = 0.1,
    attack_ratio_test: float = 0.2,
) -> Tuple[List[RecordSample], List[RecordSample]]:
    """Generate deterministic synthetic per-record quantum telemetry.

    - Benign: low QBER, moderate key rates, moderate photon counts.
    - Attack: higher QBER, lower key rates, sometimes extreme photon counts or loss.
    """

    _seed_rng()

    def sample_record(is_attack: int) -> RecordSample:
        if is_attack:
            qber = random.gauss(0.09, 0.02)
            sifted_key_rate = max(0.0, random.gauss(0.3, 0.05))
            secret_key_rate = max(0.0, sifted_key_rate - random.uniform(0.05, 0.15))
            photon_count = max(0.0, random.gauss(800.0, 200.0))
            channel_loss_db = random.gauss(6.0, 1.0)
        else:
            qber = random.gauss(0.02, 0.01)
            sifted_key_rate = max(0.0, random.gauss(0.7, 0.05))
            secret_key_rate = max(0.0, sifted_key_rate - random.uniform(0.02, 0.08))
            photon_count = max(0.0, random.gauss(500.0, 100.0))
            channel_loss_db = random.gauss(3.0, 0.5)
        return RecordSample(
            qber=qber,
            sifted_key_rate=sifted_key_rate,
            secret_key_rate=secret_key_rate,
            photon_count=photon_count,
            channel_loss_db=channel_loss_db,
            is_attack=is_attack,
        )

    def make_split(n: int, attack_ratio: float) -> List[RecordSample]:
        k_attack = int(round(n * attack_ratio))
        samples: List[RecordSample] = []
        for _ in range(k_attack):
            samples.append(sample_record(1))
        for _ in range(n - k_attack):
            samples.append(sample_record(0))
        random.shuffle(samples)
        return samples

    train = make_split(n_train, attack_ratio_train)
    test = make_split(n_test, attack_ratio_test)
    return train, test


def generate_windowed_dataset(
    n_train: int = 100,
    n_test: int = 100,
    attack_ratio_train: float = 0.1,
    attack_ratio_test: float = 0.2,
) -> Tuple[List[WindowSample], List[WindowSample]]:
    """Generate deterministic synthetic window-level telemetry.

    Each window aggregates underlying per-record metrics; we sample directly at the
    window level with behavior similar to per-record but with an attack_fraction
    feature to emulate temporal concentration of attack events.
    """

    _seed_rng()

    def sample_window(is_attack: int) -> WindowSample:
        if is_attack:
            mean_qber = random.gauss(0.08, 0.015)
            mean_secret_key_rate = max(0.0, random.gauss(0.25, 0.05))
            mean_photon_count = max(0.0, random.gauss(900.0, 150.0))
            channel_loss_db = random.gauss(6.5, 0.8)
            attack_fraction = min(1.0, max(0.0, random.gauss(0.6, 0.2)))
        else:
            mean_qber = random.gauss(0.018, 0.007)
            mean_secret_key_rate = max(0.0, random.gauss(0.72, 0.05))
            mean_photon_count = max(0.0, random.gauss(480.0, 80.0))
            channel_loss_db = random.gauss(3.2, 0.4)
            attack_fraction = min(1.0, max(0.0, random.gauss(0.02, 0.02)))
        return WindowSample(
            mean_qber=mean_qber,
            mean_secret_key_rate=mean_secret_key_rate,
            mean_photon_count=mean_photon_count,
            channel_loss_db=channel_loss_db,
            attack_fraction=attack_fraction,
            is_attack_window=is_attack,
        )

    def make_split(n: int, attack_ratio: float) -> List[WindowSample]:
        k_attack = int(round(n * attack_ratio))
        samples: List[WindowSample] = []
        for _ in range(k_attack):
            samples.append(sample_window(1))
        for _ in range(n - k_attack):
            samples.append(sample_window(0))
        random.shuffle(samples)
        return samples

    train = make_split(n_train, attack_ratio_train)
    test = make_split(n_test, attack_ratio_test)
    return train, test
