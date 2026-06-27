"""
PyTorch LSTM Model for Climate Prediction.

Architecture
------------
- Input : (batch, seq_len=30, features=3) — [fused_rainfall, fused_tmax, fused_tmin]
- LSTM  : hidden_size=128, num_layers=2, dropout=0.2
- Output: (batch, horizon=7) — next 7 days of target variable

Training
--------
- MSE loss with AdamW optimiser
- Early stopping with patience=5
- Reports RMSE and MAE on held-out validation set
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# ── Default hyper-parameters ─────────────────────────────────────
DEFAULT_SEQ_LEN = 30       # look-back window (days)
DEFAULT_HORIZON = 7        # forecast horizon (days)
DEFAULT_N_FEATURES = 3     # rainfall, tmax, tmin
DEFAULT_HIDDEN_SIZE = 128
DEFAULT_NUM_LAYERS = 2
DEFAULT_DROPOUT = 0.2
DEFAULT_LR = 1e-3
DEFAULT_EPOCHS = 100
DEFAULT_BATCH_SIZE = 64
DEFAULT_PATIENCE = 5


class ClimateLSTM(nn.Module):
    """
    Multi-step climate forecasting LSTM.

    Parameters
    ----------
    n_features : int
        Number of input features per time-step.
    hidden_size : int
        LSTM hidden state dimensionality.
    num_layers : int
        Number of stacked LSTM layers.
    dropout : float
        Dropout probability between LSTM layers.
    horizon : int
        Number of future time-steps to predict.
    """

    def __init__(
        self,
        n_features: int = DEFAULT_N_FEATURES,
        hidden_size: int = DEFAULT_HIDDEN_SIZE,
        num_layers: int = DEFAULT_NUM_LAYERS,
        dropout: float = DEFAULT_DROPOUT,
        horizon: int = DEFAULT_HORIZON,
    ) -> None:
        super().__init__()

        self.n_features = n_features
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.horizon = horizon

        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )

        # Dropout applied during stochastic forward passes at inference
        self.dropout = nn.Dropout(p=dropout)

        # Project last hidden state to multi-step forecast
        self.fc = nn.Linear(hidden_size, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Parameters
        ----------
        x : Tensor of shape (batch, seq_len, n_features)

        Returns
        -------
        Tensor of shape (batch, horizon) — predicted values for each
        future time-step.
        """
        # lstm_out: (batch, seq_len, hidden_size)
        lstm_out, _ = self.lstm(x)

        # Take the output at the last time-step
        last_hidden = lstm_out[:, -1, :]  # (batch, hidden_size)

        # Apply dropout (active when model.train() for MC-Dropout)
        dropped = self.dropout(last_hidden)

        # Project to forecast horizon
        out = self.fc(dropped)  # (batch, horizon)

        return out


# ── Training utilities ───────────────────────────────────────────
def compute_metrics(
    predictions: np.ndarray,
    targets: np.ndarray,
) -> dict[str, float]:
    """Compute RMSE and MAE from numpy arrays."""
    mse = np.mean((predictions - targets) ** 2)
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(predictions - targets)))
    return {"rmse": rmse, "mae": mae}


def train_model(
    model: ClimateLSTM,
    train_X: np.ndarray,
    train_y: np.ndarray,
    val_X: np.ndarray,
    val_y: np.ndarray,
    epochs: int = DEFAULT_EPOCHS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    lr: float = DEFAULT_LR,
    patience: int = DEFAULT_PATIENCE,
    device: str | None = None,
) -> dict[str, Any]:
    """
    Train the LSTM model with early stopping.

    Parameters
    ----------
    model : ClimateLSTM instance.
    train_X : ndarray of shape (n_samples, seq_len, n_features).
    train_y : ndarray of shape (n_samples, horizon).
    val_X, val_y : validation arrays (same shapes).
    epochs : max training epochs.
    batch_size : mini-batch size.
    lr : learning rate.
    patience : early stopping patience (epochs without improvement).
    device : "cuda", "cpu", or None (auto-detect).

    Returns
    -------
    dict with keys: best_epoch, best_val_rmse, best_val_mae,
    train_history, val_history.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model = model.to(device)

    # Convert to tensors
    train_X_t = torch.FloatTensor(train_X).to(device)
    train_y_t = torch.FloatTensor(train_y).to(device)
    val_X_t = torch.FloatTensor(val_X).to(device)
    val_y_t = torch.FloatTensor(val_y).to(device)

    # DataLoader via TensorDataset
    train_dataset = torch.utils.data.TensorDataset(train_X_t, train_y_t)
    train_loader = torch.utils.data.DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
    )

    criterion = nn.MSELoss()
    optimiser = torch.optim.AdamW(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimiser, mode="min", factor=0.5, patience=3
    )

    best_val_loss = float("inf")
    best_epoch = 0
    best_state = None
    epochs_without_improvement = 0

    train_history: list[dict[str, float]] = []
    val_history: list[dict[str, float]] = []

    for epoch in range(1, epochs + 1):
        # ── Train ────────────────────────────────────────────────
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for batch_X, batch_y in train_loader:
            optimiser.zero_grad()
            preds = model(batch_X)
            loss = criterion(preds, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimiser.step()
            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / max(n_batches, 1)

        # ── Validate ─────────────────────────────────────────────
        model.eval()
        val_preds_list = []
        val_loss_sum = 0.0
        val_batches = 0

        with torch.no_grad():
            for i in range(0, len(val_X_t), batch_size):
                batch_X = val_X_t[i:i+batch_size]
                batch_y = val_y_t[i:i+batch_size]
                
                preds = model(batch_X)
                loss = criterion(preds, batch_y)
                
                val_loss_sum += loss.item()
                val_batches += 1
                val_preds_list.append(preds.cpu().numpy())

        val_loss = val_loss_sum / max(val_batches, 1)
        val_preds_np = np.concatenate(val_preds_list, axis=0)
        val_y_np = val_y_t.cpu().numpy()
        val_metrics = compute_metrics(val_preds_np, val_y_np)

        train_rmse = float(np.sqrt(train_loss))
        train_history.append({"loss": train_loss, "rmse": train_rmse})
        val_history.append({"loss": val_loss, **val_metrics})

        scheduler.step(val_loss)

        # ── Early stopping ───────────────────────────────────────
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        # ── Logging ──────────────────────────────────────────────
        lr_current = optimiser.param_groups[0]["lr"]
        logger.info(
            "Epoch %3d/%d │ Train RMSE: %.4f │ Val RMSE: %.4f │ "
            "Val MAE: %.4f │ LR: %.6f%s",
            epoch, epochs, train_rmse, val_metrics["rmse"],
            val_metrics["mae"], lr_current,
            " ★" if epoch == best_epoch else "",
        )

        if epochs_without_improvement >= patience:
            logger.info(
                "Early stopping at epoch %d (patience=%d)",
                epoch, patience,
            )
            break

    # Restore best weights
    if best_state is not None:
        model.load_state_dict(best_state)
        model = model.to(device)

    # Final validation metrics with best model
    model.eval()
    final_preds_list = []
    with torch.no_grad():
        for i in range(0, len(val_X_t), batch_size):
            batch_X = val_X_t[i:i+batch_size]
            final_preds_list.append(model(batch_X).cpu().numpy())
            
    final_preds = np.concatenate(final_preds_list, axis=0)

    final_metrics = compute_metrics(final_preds, val_y_t.cpu().numpy())

    return {
        "best_epoch": best_epoch,
        "best_val_rmse": final_metrics["rmse"],
        "best_val_mae": final_metrics["mae"],
        "train_history": train_history,
        "val_history": val_history,
    }
