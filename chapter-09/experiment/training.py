import math
from typing import List, Sequence, Tuple

from .utils import mse, sigmoid


def _bce_loss(pred: float, target: int) -> float:
    eps = 1e-8
    p = min(max(pred, eps), 1.0 - eps)
    if target == 1:
        return -math.log(p)
    else:
        return -math.log(1.0 - p)


def train_classifier(
    model,
    X_train: Sequence,
    y_train: Sequence[int],
    X_val: Sequence,
    y_val: Sequence[int],
    epochs: int = 20,
    lr: float = 0.1,
) -> None:
    """Train a simple classifier.

    The model must implement either:
      - parameters()/update_parameters() for vector models, or
      - predict_proba_one(seq) and custom attribute access for simple models.

    For sequence models (SimpleSequenceModel), we perform manual backprop
    through its internal structure using pooled inputs.
    """
    # Handle three model families via duck typing
    if hasattr(model, "parameters"):
        # vector-like models (StaticBaselineClassifier, GraphContextModel)
        w, b_list = model.parameters()
        for _ in range(epochs):
            # full-batch gradient
            grad_w = [0.0 for _ in w]
            grad_b = 0.0
            n = float(len(X_train)) if X_train else 1.0
            for x, y in zip(X_train, y_train):
                if isinstance(x, tuple):
                    # GraphContextModel: concat handled inside
                    p = model.predict_proba_one(x)
                    x_vec = model._concat(x)  # type: ignore[attr-defined]
                else:
                    p = model.predict_proba_one(x)
                    x_vec = x
                # gradient of BCE wrt logit z is (p - y)
                dz = p - float(y)
                for i, xi in enumerate(x_vec):
                    grad_w[i] += dz * xi / n
                grad_b += dz / n
            # gradient step
            for i in range(len(w)):
                w[i] -= lr * grad_w[i]
            b_list[0] -= lr * grad_b
            model.update_parameters(w, b_list)
        return

    # Sequence model (SimpleSequenceModel) - approximate gradient on pooled vector
    if hasattr(model, "_forward_vector") and hasattr(model, "_linear1"):
        input_dim = model.input_dim
        hidden_dim = model.hidden_dim
        for _ in range(epochs):
            # full-batch gradient
            grad_w1 = [0.0 for _ in model.w1]
            grad_b1 = [0.0 for _ in model.b1]
            grad_w2 = [0.0 for _ in model.w2]
            grad_b2 = 0.0
            n = float(len(X_train)) if X_train else 1.0
            for seq, y in zip(X_train, y_train):
                if not seq:
                    continue
                length = len(seq)
                pooled = [0.0 for _ in range(input_dim)]
                for t in seq:
                    for i, v in enumerate(t):
                        pooled[i] += v
                pooled = [v / float(length) for v in pooled]
                # forward
                z1 = model._linear1(pooled)
                h = model._relu(z1)
                z2 = 0.0
                for j in range(hidden_dim):
                    z2 += model.w2[j] * h[j]
                z2 += model.b2
                p = sigmoid(z2)
                dz2 = p - float(y)
                # grads for w2, b2, h
                for j in range(hidden_dim):
                    grad_w2[j] += dz2 * h[j] / n
                grad_b2 += dz2 / n
                dh = [dz2 * model.w2[j] for j in range(hidden_dim)]
                # backprop through ReLU
                dz1 = [dh[j] if z1[j] > 0.0 else 0.0 for j in range(hidden_dim)]
                # grads for w1, b1
                for j in range(hidden_dim):
                    start = j * input_dim
                    for i in range(input_dim):
                        grad_w1[start + i] += dz1[j] * pooled[i] / n
                    grad_b1[j] += dz1[j] / n
            # update
            for i in range(len(model.w1)):
                model.w1[i] -= lr * grad_w1[i]
            for j in range(len(model.b1)):
                model.b1[j] -= lr * grad_b1[j]
            for j in range(len(model.w2)):
                model.w2[j] -= lr * grad_w2[j]
            model.b2 -= lr * grad_b2
        return

    # If we reach here, model type is unsupported for training
    raise TypeError("Unsupported model type for train_classifier")


def evaluate_classifier(model, X: Sequence, y: Sequence[int]) -> float:
    if not X:
        return 0.0
    correct = 0
    total = len(X)
    for x, label in zip(X, y):
        pred = model.predict_one(x)
        if pred == label:
            correct += 1
    return float(correct) / float(total)


def train_autoencoder_detector(
    model,
    X_train: Sequence[List[float]],
    y_train: Sequence[int],
    X_val: Sequence[List[float]],
    y_val: Sequence[int],
    epochs: int = 30,
    lr: float = 0.05,
) -> float:
    """Train the autoencoder on negative (label 0) samples and return a
    reconstruction-error threshold selected on validation negatives.

    The threshold is the 95th percentile of reconstruction errors on
    validation negatives.
    """
    # Filter negatives
    neg_train = [x for x, lbl in zip(X_train, y_train) if lbl == 0]
    if not neg_train:
        neg_train = list(X_train)

    n = float(len(neg_train)) if neg_train else 1.0

    for _ in range(epochs):
        # full-batch gradient descent
        grad_W = [0.0 for _ in model.W]
        grad_b1 = [0.0 for _ in model.b1]
        grad_b2 = [0.0 for _ in model.b2]

        for x in neg_train:
            # forward
            h = model._encode(x)
            x_hat = model._decode(h)
            # gradient of MSE wrt x_hat: 2*(x_hat - x)/D
            D = float(len(x)) if x else 1.0
            dL_dxhat = [2.0 * (xh - xv) / D for xh, xv in zip(x_hat, x)]
            # backprop to decoder params (W^T and b2)
            for i in range(model.input_dim):
                grad_b2[i] += dL_dxhat[i] / n
                for j in range(model.hidden_dim):
                    w_index = j * model.input_dim + i
                    grad_W[w_index] += dL_dxhat[i] * h[j] / n
            # backprop to h
            dL_dh = [0.0 for _ in range(model.hidden_dim)]
            for j in range(model.hidden_dim):
                s = 0.0
                for i in range(model.input_dim):
                    w_index = j * model.input_dim + i
                    s += dL_dxhat[i] * model.W[w_index]
                dL_dh[j] = s
            # backprop through ReLU encoder to W and b1
            for j in range(model.hidden_dim):
                if h[j] <= 0.0:
                    continue
                for i in range(model.input_dim):
                    w_index = j * model.input_dim + i
                    grad_W[w_index] += dL_dh[j] * x[i] / n
                grad_b1[j] += dL_dh[j] / n

        # gradient step
        for k in range(len(model.W)):
            model.W[k] -= lr * grad_W[k]
        for j in range(len(model.b1)):
            model.b1[j] -= lr * grad_b1[j]
        for i in range(len(model.b2)):
            model.b2[i] -= lr * grad_b2[i]

    # Choose threshold from validation negatives
    val_neg_scores = [
        model.anomaly_score(x)
        for x, lbl in zip(X_val, y_val)
        if lbl == 0
    ]
    if not val_neg_scores:
        val_neg_scores = [model.anomaly_score(x) for x in X_val] or [0.0]
    sorted_scores = sorted(val_neg_scores)
    idx = int(0.95 * (len(sorted_scores) - 1))
    threshold = float(sorted_scores[idx])
    return threshold


def evaluate_autoencoder_detector(
    model,
    threshold: float,
    X: Sequence[List[float]],
    y: Sequence[int],
) -> float:
    if not X:
        return 0.0
    correct = 0
    total = len(X)
    for x, label in zip(X, y):
        score = model.anomaly_score(x)
        pred = 1 if score > threshold else 0
        if pred == label:
            correct += 1
    return float(correct) / float(total)
