"""Stop a fine-tuning run that is going wrong (pure Python, so it is testable without MLX).

The run that motivated it: peak learning rate 1e-4 without gradient clipping; the training loss went 1.17 -> 2.35 -> 3.03 -> 4.52 ->
10.86 and the validation loss 1.81 -> 2.67 -> 6.88 within 155 steps; it was noticed after 5.5 hours, when every checkpoint was
already damaged. The guard would have stopped it at step 56 (training loss 3.03) and, at the latest, at step 77 (validation loss 2.67
against 1.81 for the untrained model)."""
from __future__ import annotations


class TrainingDiverged(Exception):
    pass


def make_guard(first_val_factor: float = 1.3, train_limit: float = 3.0, ignore_first_reports: int = 3):
    """-> (on_train_report, on_val_report). Each takes the report dict of mlx_lm's trainer and raises TrainingDiverged.
    The first validation report (step 0) is the untrained model's loss and becomes the reference."""
    state = {"first_val": None, "reports": 0}

    def on_train(info: dict) -> None:
        state["reports"] += 1
        if state["reports"] > ignore_first_reports and info["train_loss"] > train_limit:
            raise TrainingDiverged(f"training loss {info['train_loss']:.2f} > {train_limit} at step {info['iteration']}")

    def on_val(info: dict) -> None:
        if state["first_val"] is None:
            state["first_val"] = info["val_loss"]
        elif info["val_loss"] > state["first_val"] * first_val_factor:
            raise TrainingDiverged(f"validation loss {info['val_loss']:.3f} > {first_val_factor} x the untrained model's "
                                   f"{state['first_val']:.3f} at step {info['iteration']}")

    return on_train, on_val
