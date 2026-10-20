from collections import namedtuple

Schedule = namedtuple("Schedule", "start makespan")


class CycleError(Exception):
    pass


def schedule(tasks, capacity):
    by_name = {t["name"]: t for t in tasks}
    deps = {t["name"]: list(t.get("deps", [])) for t in tasks}
    start, finished, running = {}, set(), []   # running: (end, name)
    time, free = 0, capacity
    pending = [t["name"] for t in tasks]
    while pending or running:
        # sort by duration (naive priority)
        pending.sort(key=lambda n: (-by_name[n]["duration"], n))
        for name in list(pending):
            if all(d in finished for d in deps[name]):
                cpus = by_name[name].get("cpus", 1)
                if cpus > free:
                    break
                start[name] = time
                free -= cpus
                running.append((time + by_name[name]["duration"], name))
                pending.remove(name)
        if not running:
            break
        running.sort()
        end, name = running.pop(0)
        time = end
        finished.add(name)
        free += by_name[name].get("cpus", 1)
    makespan = max((start[n] + by_name[n]["duration"] for n in start), default=0)
    return Schedule(start, makespan)
