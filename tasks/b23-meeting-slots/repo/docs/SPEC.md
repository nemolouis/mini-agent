# Meeting slot finder

`find_slot(busy, duration_minutes, after, work_start=9, work_end=17, horizon_days=60)`

- `busy`: dict mapping person -> list of `(start, end)` naive datetimes. Intervals are
  half-open `[start, end)`. Intervals with `start >= end` are ignored.
- `duration_minutes`: a positive multiple of 5, otherwise `ValueError`.
- A meeting is `[s, s + duration)`. It is acceptable when
  * `s` is on the 5-minute grid (minute % 5 == 0, zero seconds and microseconds);
  * `s >= after`;
  * it lies entirely inside the working hours of ONE day: `work_start:00 <= s` and
    `s + duration <= work_end:00` on the same date, and that date is a weekday (Mon-Fri);
  * it does not overlap any busy interval of any person. Touching is fine: a meeting may
    start exactly when a busy interval ends and end exactly when one starts.
- The result is the earliest acceptable `s`, or `None` if there is none within
  `horizon_days` days after `after`'s date (inclusive of that date).
