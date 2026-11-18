from typing import List, Tuple

from .utils import dot, mse, sigmoid


class StaticBaselineClassifier:
    """Simple logistic regression classifier implemented from scratch.

    Parameters are a weight vector and bias. Trained with gradient descent
    on binary cross-entropy.
    """

    def __init__(self, input_dim: int):
        self.w = [0.0 for _ in range(input_dim)]
        self.b = 0.0

    def predict_proba_one(self, x: List[float]) -> float:
        return sigmoid(dot(self.w, x) + self.b)

    def predict_one(self, x: List[float]) -> int:
        return 1 if self.predict_proba_one(x) >= 0.5 else 0

    def parameters(self) -> Tuple[List[float], List[float]]:
        # return references to weight list and [bias] for unified updates
        return self.w, [self.b]

    def update_parameters(self, w: List[float], b_list: List[float]) -> None:
        self.w = w
        self.b = b_list[0]


class SimpleSequenceModel:
    """Very small sequence model.

    It computes a mean-pooled feature vector over time, then applies a
    one-hidden-layer MLP and a sigmoid output. This captures some temporal
    structure via aggregation.
    """

    def __init__(self, input_dim: int, hidden_dim: int = 8):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        # Initialize weights with small values
        self.w1 = [0.0 for _ in range(input_dim * hidden_dim)]
        self.b1 = [0.0 for _ in range(hidden_dim)]
        self.w2 = [0.0 for _ in range(hidden_dim)]
        self.b2 = 0.0

    def _linear1(self, x: List[float]) -> List[float]:
        # x: input_dim, W1: hidden_dim x input_dim (stored row-major)
        out = []
        for h in range(self.hidden_dim):
            start = h * self.input_dim
            w_row = self.w1[start : start + self.input_dim]
            out.append(dot(w_row, x) + self.b1[h])
        return out

    def _relu(self, v: List[float]) -> List[float]:
        return [x if x > 0.0 else 0.0 for x in v]

    def _forward_vector(self, x: List[float]) -> float:
        # Mean-pooled sequence already; this is vector path
        h = self._linear1(x)
        h = self._relu(h)
        out = dot(self.w2, h) + self.b2
        return sigmoid(out)

    def predict_proba_one(self, seq: List[List[float]]) -> float:
        if not seq:
            return 0.0
        # mean over time dimension
        length = len(seq)
        dim = len(seq[0])
        acc = [0.0] * dim
        for t in seq:
            for i, v in enumerate(t):
                acc[i] += v
        pooled = [v / float(length) for v in acc]
        return self._forward_vector(pooled)

    def predict_one(self, seq: List[List[float]]) -> int:
        return 1 if self.predict_proba_one(seq) >= 0.5 else 0


class GraphContextModel:
    """Tiny model using local and neighbor-aggregated features.

    It concatenates local and neighbor features and applies a logistic
    regression-like layer.
    """

    def __init__(self, local_dim: int, neighbor_dim: int):
        self.local_dim = local_dim
        self.neighbor_dim = neighbor_dim
        self.w = [0.0 for _ in range(local_dim + neighbor_dim)]
        self.b = 0.0

    def _concat(self, sample: Tuple[List[float], List[float]]) -> List[float]:
        local, neigh = sample
        return list(local) + list(neigh)

    def predict_proba_one(self, sample: Tuple[List[float], List[float]]) -> float:
        x = self._concat(sample)
        return sigmoid(dot(self.w, x) + self.b)

    def predict_one(self, sample: Tuple[List[float], List[float]]) -> int:
        return 1 if self.predict_proba_one(sample) >= 0.5 else 0

    def parameters(self) -> Tuple[List[float], List[float]]:
        return self.w, [self.b]

    def update_parameters(self, w: List[float], b_list: List[float]) -> None:
        self.w = w
        self.b = b_list[0]


class SimpleAutoencoderDetector:
    """Simple autoencoder-like model for vector inputs.

    This is a single hidden layer linear autoencoder with tied weights:
    x -> h = ReLU(Wx + b1) -> x_hat = W^T h + b2.
    The anomaly score is the mean squared reconstruction error.
    """

    def __init__(self, input_dim: int, hidden_dim: int = 8):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.W = [0.0 for _ in range(input_dim * hidden_dim)]  # row-major: h x in
        self.b1 = [0.0 for _ in range(hidden_dim)]
        self.b2 = [0.0 for _ in range(input_dim)]

    def _encode(self, x: List[float]) -> List[float]:
        h = []
        for j in range(self.hidden_dim):
            start = j * self.input_dim
            w_row = self.W[start : start + self.input_dim]
            v = dot(w_row, x) + self.b1[j]
            h.append(v if v > 0.0 else 0.0)
        return h

    def _decode(self, h: List[float]) -> List[float]:
        # Using W^T for decoding
        x_hat = []
        for i in range(self.input_dim):
            s = 0.0
            for j in range(self.hidden_dim):
                w_ji = self.W[j * self.input_dim + i]
                s += w_ji * h[j]
            x_hat.append(s + self.b2[i])
        return x_hat

    def reconstruct(self, x: List[float]) -> List[float]:
        h = self._encode(x)
        return self._decode(h)

    def anomaly_score(self, x: List[float]) -> float:
        x_hat = self.reconstruct(x)
        return mse(x, x_hat)
