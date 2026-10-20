from miniagent.trainguard import TrainingDiverged, make_guard

# the reports of the run that diverged (lr 1e-4, no clipping): (step, training loss) every 8 steps, validation (step, loss)
TRAIN = [(8, 1.608), (16, 1.611), (24, 1.19), (32, 1.17), (40, 2.35), (48, 1.17), (56, 3.03), (64, 4.52), (72, 4.84), (80, 2.86),
         (88, 2.33), (96, 4.14), (104, 10.86)]
VAL = [(0, 1.812), (77, 2.668), (155, 6.876)]


def replay(guard_kwargs, train=TRAIN, val=VAL):
    on_train, on_val = make_guard(**guard_kwargs)
    events = sorted([(i, "val", v) for i, v in val] + [(i, "train", v) for i, v in train])
    for step, kind, value in events:
        try:
            if kind == "train":
                on_train({"iteration": step, "train_loss": value})
            else:
                on_val({"iteration": step, "val_loss": value})
        except TrainingDiverged as e:
            return step, str(e)
    return None, ""


def test_the_guard_would_have_stopped_the_diverged_run_at_step_56():
    step, why = replay({})
    assert step == 56 and "training loss 3.03" in why


def test_the_validation_check_alone_stops_it_at_step_77():
    step, why = replay({"train_limit": 99.0})
    assert step == 77 and "validation loss 2.668" in why and "1.812" in why


def test_a_healthy_run_is_not_stopped():
    train = [(8, 1.6), (16, 1.5), (24, 1.4), (32, 1.45), (40, 1.2), (48, 1.1)]
    val = [(0, 1.81), (40, 1.5), (80, 1.2)]
    assert replay({}, train, val)[0] is None


def test_early_noise_is_ignored_for_the_training_loss_but_not_for_validation():
    assert replay({}, [(8, 3.5), (16, 3.2), (24, 3.1)], [(0, 1.8)])[0] is None          # the first reports are not judged
    assert replay({}, [(8, 3.5), (16, 3.2), (24, 3.1), (32, 3.1)], [(0, 1.8)])[0] == 32
    assert replay({}, [(8, 1.5)], [(0, 1.8), (10, 2.4)])[0] == 10                      # 2.4 > 1.3 x 1.8


def test_the_threshold_is_exclusive():
    assert replay({"first_val_factor": 1.5}, [], [(0, 2.0), (10, 3.0)])[0] is None
    assert replay({"first_val_factor": 1.5}, [], [(0, 2.0), (10, 3.001)])[0] == 10
