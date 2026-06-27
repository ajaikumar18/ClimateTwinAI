"""
LSTM Training CLI Script.

Trains a ClimateLSTM model on fused IMD + INSAT satellite data for a
specified climate variable.  Saves the best model and scaler to the
``models/`` directory.

Usage
-----
    # Train rainfall model:
    python -m scripts.train_model --variable rainfall --epochs 100

    # Train temperature max:
    python -m scripts.train_model --variable tmax --epochs 50

    # Quick test with fewer epochs:
    python -m scripts.train_model --variable tmin --epochs 10
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import torch
torch.set_num_threads(1)

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.session import AsyncSessionLocal
from app.ai.lstm_model import (
    ClimateLSTM,
    train_model,
    compute_metrics,
    DEFAULT_SEQ_LEN,
    DEFAULT_HORIZON,
    DEFAULT_HIDDEN_SIZE,
    DEFAULT_NUM_LAYERS,
    DEFAULT_DROPOUT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_PATIENCE,
)
from app.ai.data_loader import prepare_training_data, MODELS_DIR

logger = logging.getLogger(__name__)

DIVIDER = "=" * 64
THIN = "─" * 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train LSTM climate prediction model on fused data",
    )
    parser.add_argument(
        "--variable",
        type=str,
        required=True,
        choices=["rainfall", "tmax", "tmin"],
        help="Target climate variable to predict",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Maximum training epochs (default: 100)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Mini-batch size (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate (default: 0.001)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=DEFAULT_PATIENCE,
        help=f"Early stopping patience (default: {DEFAULT_PATIENCE})",
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2025-01-01",
        help="Training data start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2025-12-31",
        help="Training data end date (YYYY-MM-DD)",
    )
    return parser.parse_args()


async def main() -> None:
    setup_logging()
    args = parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(DIVIDER)
    print("  ClimateTwin AI — LSTM Model Training")
    print(DIVIDER)
    print(f"    Variable     : {args.variable}")
    print(f"    Date range   : {start.date()} → {end.date()}")
    print(f"    Epochs       : {args.epochs}")
    print(f"    Batch size   : {args.batch_size}")
    print(f"    Learning rate: {args.lr}")
    print(f"    Patience     : {args.patience}")
    print(f"    Device       : {device}")
    print(f"    LSTM config  : hidden={DEFAULT_HIDDEN_SIZE}, "
          f"layers={DEFAULT_NUM_LAYERS}, dropout={DEFAULT_DROPOUT}")
    print(f"    Sequence     : {DEFAULT_SEQ_LEN} days → {DEFAULT_HORIZON} days")
    print(DIVIDER)

    # ── Step 1: Prepare data ─────────────────────────────────────
    print(f"\n{THIN}")
    print("  Step 1: Loading and preparing fused training data...")
    print(THIN)

    t0 = time.time()

    async with AsyncSessionLocal() as session:
        data = await prepare_training_data(
            db=session,
            target_variable=args.variable,
            start=start,
            end=end,
        )

    data_time = time.time() - t0

    print(f"\n    Grid cells used   : {data['n_cells']}")
    print(f"    Days per cell     : {data['n_days']}")
    print(f"    Features          : {data['feature_names']}")
    print(f"    Train samples     : {len(data['train_X']):,}")
    print(f"    Val samples       : {len(data['val_X']):,}")
    print(f"    Target column idx : {data['target_col_idx']}")
    print(f"    Data load time    : {data_time:.1f}s")

    if len(data["train_X"]) == 0:
        print("\n    ✘ No training samples generated. Check data availability.")
        return

    # ── Step 2: Train model ──────────────────────────────────────
    print(f"\n{THIN}")
    print("  Step 2: Training LSTM model...")
    print(THIN)

    model = ClimateLSTM(
        n_features=len(data["feature_names"]),
        hidden_size=DEFAULT_HIDDEN_SIZE,
        num_layers=DEFAULT_NUM_LAYERS,
        dropout=DEFAULT_DROPOUT,
        horizon=DEFAULT_HORIZON,
    )

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n    Model parameters: {total_params:,} total, {trainable_params:,} trainable")

    t0 = time.time()

    results = train_model(
        model=model,
        train_X=data["train_X"],
        train_y=data["train_y"],
        val_X=data["val_X"],
        val_y=data["val_y"],
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
        device=device,
    )

    train_time = time.time() - t0

    # ── Step 3: Save model ───────────────────────────────────────
    print(f"\n{THIN}")
    print("  Step 3: Saving best model...")
    print(THIN)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"lstm_{args.variable}.pt"
    torch.save(model.state_dict(), str(model_path))
    print(f"    ✔ Model saved to {model_path}")
    print(f"    ✔ Scaler saved to {MODELS_DIR / f'scaler_{args.variable}.pkl'}")

    # ── Final summary ────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  Training Summary — for ISRO Hackathon Judges")
    print(DIVIDER)

    unit = {"rainfall": "mm", "tmax": "°C", "tmin": "°C"}[args.variable]

    print(f"""
    ┌─────────────────────────────────────────────────────┐
    │  Variable        : {args.variable:<30} │
    │  Unit            : {unit:<30} │
    │  Date range      : {str(start.date()) + ' → ' + str(end.date()):<30} │
    │  Grid cells      : {str(data['n_cells']):<30} │
    │  Train samples   : {str(f"{len(data['train_X']):,}"):<30} │
    │  Val samples     : {str(f"{len(data['val_X']):,}"):<30} │
    │  Best epoch      : {str(results['best_epoch']):<30} │
    │  ─────────────────────────────────────────────────── │
    │  Val RMSE        : {f"{results['best_val_rmse']:.4f} {unit}":<30} │
    │  Val MAE         : {f"{results['best_val_mae']:.4f} {unit}":<30} │
    │  ─────────────────────────────────────────────────── │
    │  Data sources    : IMD Ground + INSAT Satellite      │
    │  Fusion method   : Weighted (0.6×IMD + 0.4×INSAT)    │
    │  Uncertainty     : MC-Dropout (10 passes)            │
    │  Training time   : {f"{train_time:.1f}s":<30} │
    │  Device          : {device:<30} │
    └─────────────────────────────────────────────────────┘
    """)

    print(DIVIDER)
    print("  Done. Model ready for inference via POST /api/v1/predict")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())
