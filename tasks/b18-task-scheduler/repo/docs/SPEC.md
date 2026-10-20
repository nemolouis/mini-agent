# Deterministic task scheduler

`schedule(tasks, capacity)` simulates running dependent tasks on `capacity` CPUs and returns
`Schedule(start, makespan)`.

A task is a dict: `name` (str, unique), `duration` (int >= 1), optional `deps` (list of
names, default `[]`), optional `cpus` (int >= 1, default 1). Tasks may not be pre-empted.

## Validation (raise before simulating)
- duplicate names, an unknown dependency, `duration < 1`, `cpus < 1` or `cpus > capacity`
  raise `ValueError`; a dependency cycle (including a self-dependency) raises `CycleError`.

## Priority
`priority(t)` = the length of the longest chain of dependants starting at t, counting
the durations of every task on the chain including t itself (its critical path length).
Larger priority is more urgent. Ties are broken by task name, ascending.

## Simulation
Time starts at 0 with `capacity` free CPUs. Repeat until every task has finished:
1. Finish **all** running tasks whose end time equals the current time, releasing their CPUs.
2. Let *ready* be the tasks not yet started whose dependencies have all finished.
   Go through the ready tasks ordered by (higher priority first, then name). Start a task
   now (at the current time) if its `cpus` fit in the free CPUs; a task that does not fit is
   skipped and later (less urgent) ready tasks may still start.
3. Advance time to the earliest end time among running tasks.

`start` maps every task name to its start time; `makespan` is the latest end time
(0 for an empty task list).
