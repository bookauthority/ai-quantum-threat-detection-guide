from dataclasses import dataclass
from typing import Any


@dataclass
class RNG:
    """Simple deterministic RNG wrapper using Python's random.Random.

    This makes it easy to pass around an explicit RNG instance instead of
    relying on global state, supporting reproducibility.
    """

    seed: int

    def __post_init__(self) -> None:
        import random

        self._r = random.Random(self.seed)

    def random(self) -> float:
        return self._r.random()

    def randint(self, a: int, b: int) -> int:
        return self._r.randint(a, b)

    def choice(self, seq: Any) -> Any:
        return self._r.choice(seq)

    def uniform(self, a: float, b: float) -> float:
        return self._r.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._r.gauss(mu, sigma)


def binomial(trials: int, p: float, rng: RNG) -> int:
    """Naive binomial sampler using independent Bernoulli trials.

    This is efficient enough for the small to moderate trial counts used in
    this experiment. The result is deterministic given the RNG.
    """

    if trials <= 0:
        return 0
    if p <= 0.0:
        return 0
    if p >= 1.0:
        return trials
    count = 0
    for _ in range(trials):
        if rng.random() < p:
            count += 1
    return count
