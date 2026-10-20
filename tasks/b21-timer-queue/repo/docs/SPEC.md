# TimerQueue

A deterministic timer queue driven by a clock object with `now()` and `set(t)`.
`FakeClock` (in clock.py) implements both.

## API
- `call_later(delay, fn, *args)` -> `Handle`; `delay >= 0` else `ValueError`.
  The timer is due at `clock.now() + delay`.
- `call_every(interval, fn, *args, first_delay=None)` -> `Handle`; `interval > 0` else
  `ValueError`. First due time is `now + first_delay` (default: `now + interval`).
- `cancel(handle)` -> `True` if the timer was still pending (it will not run again),
  `False` otherwise (already finished, or already cancelled).
- `run_until(t)` -> number of callbacks executed. `t >= clock.now()` else `ValueError`.
- `pending()` -> number of timers that are not cancelled and not finished
  (a repeating timer stays pending until cancelled).
- `errors` -> list of exceptions raised by callbacks, in the order they occurred.
- `Handle` has `.due` (next due time) and `.cancelled`.

## Semantics of run_until(t)
- Timers run in order of `(due time, creation order)`.
- Before a callback runs, the clock is set to that timer's due time (so `clock.now()` inside
  a callback is the due time, not `t`). After the last timer due at or before `t`,
  the clock is set to `t`.
- Timers created by a running callback are relative to the clock's current time. If such a
  timer is due at or before `t` it also runs during this call, ordered after every timer
  that already exists with an equal due time.
- A repeating timer's next due time is its previous due time plus the interval (it does not
  drift, whatever the clock says). A repeating timer that is cancelled by its own callback
  does not run again.
- A callback that raises does not stop the loop: the exception is appended to `errors`,
  the callback still counts as executed, and a repeating timer keeps repeating.
