from collections import namedtuple

Schedule = namedtuple("Schedule", "start makespan")


class CycleError(Exception):
    pass


def schedule(tasks, capacity):
    by = {}
    for t in tasks:
        n = t["name"]
        if n in by:
            raise ValueError(f"duplicate task {n!r}")
        if t["duration"] < 1:
            raise ValueError(f"task {n!r} has duration < 1")
        cpus = t.get("cpus", 1)
        if cpus < 1 or cpus > capacity:
            raise ValueError(f"task {n!r} needs {cpus} cpus (capacity {capacity})")
        by[n] = {"duration": t["duration"], "deps": list(t.get("deps", [])), "cpus": cpus}
    for n, t in by.items():
        for d in t["deps"]:
            if d not in by:
                raise ValueError(f"task {n!r} depends on unknown task {d!r}")

    children = {n: [] for n in by}
    for n, t in by.items():
        for d in t["deps"]:
            children[d].append(n)

    # priority = critical path length; cycle detection by DFS colouring
    prio, state = {}, {}

    def visit(n):
        if state.get(n) == 2:
            return prio[n]
        if state.get(n) == 1:
            raise CycleError(n)
        state[n] = 1
        best = max((visit(c) for c in children[n]), default=0)
        prio[n] = by[n]["duration"] + best
        state[n] = 2
        return prio[n]

    for n in sorted(by):
        visit(n)

    start, finished, running = {}, set(), []   # running: (end, name)
    time, free = 0, capacity
    unstarted = set(by)
    while unstarted or running:
        for end, name in [r for r in running if r[0] == time]:
            running.remove((end, name))
            finished.add(name)
            free += by[name]["cpus"]
        ready = sorted((n for n in unstarted if all(d in finished for d in by[n]["deps"])),
                       key=lambda n: (-prio[n], n))
        for n in ready:
            if by[n]["cpus"] <= free:
                start[n] = time
                free -= by[n]["cpus"]
                running.append((time + by[n]["duration"], n))
                unstarted.discard(n)
        if not running:
            break
        time = min(e for e, _ in running)
    makespan = max((start[n] + by[n]["duration"] for n in start), default=0)
    return Schedule(start, makespan)
