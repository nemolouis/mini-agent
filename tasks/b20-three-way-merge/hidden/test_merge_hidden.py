import random
from merge import merge3

C0, C1, C2 = "<<<<<<< ours", "=======", ">>>>>>> theirs"


def test_changes_in_different_regions_both_apply():
    base = ["a", "b", "c", "d", "e"]
    r = merge3(base, ["a", "B", "c", "d", "e"], ["a", "b", "c", "d", "E"])
    assert r.lines == ["a", "B", "c", "d", "E"] and r.conflicts == 0


def test_same_line_changed_differently_conflicts():
    r = merge3(["a", "b", "c"], ["a", "X", "c"], ["a", "Y", "c"])
    assert r.lines == ["a", C0, "X", C1, "Y", C2, "c"] and r.conflicts == 1


def test_identical_changes_merge_cleanly():
    r = merge3(["a", "b", "c"], ["a", "X", "c"], ["a", "X", "c"])
    assert r.lines == ["a", "X", "c"] and r.conflicts == 0


def test_delete_vs_unchanged():
    r = merge3(["a", "b", "c"], ["a", "c"], ["a", "b", "c"])
    assert r == (["a", "c"], 0)
    r = merge3(["a", "b", "c"], ["a", "b", "c"], ["a", "c"])
    assert r == (["a", "c"], 0)


def test_delete_vs_edit_conflicts():
    r = merge3(["a", "b", "c"], ["a", "c"], ["a", "B", "c"])
    assert r.lines == ["a", C0, C1, "B", C2, "c"] and r.conflicts == 1


def test_inserts_at_same_place_conflict_or_agree():
    r = merge3(["a", "c"], ["a", "x", "c"], ["a", "y", "c"])
    assert r.lines == ["a", C0, "x", C1, "y", C2, "c"] and r.conflicts == 1
    r = merge3(["a", "c"], ["a", "x", "c"], ["a", "x", "c"])
    assert r == (["a", "x", "c"], 0)


def test_inserts_at_start_and_end():
    r = merge3(["a", "b"], ["x", "a", "b"], ["a", "b", "y"])
    assert r == (["x", "a", "b", "y"], 0)


def test_adjacent_changes_in_one_region_conflict():
    r = merge3(["a", "b", "c"], ["a", "b", "X", "c"], ["a", "B", "c"])
    assert r.lines == ["a", C0, "b", "X", C1, "B", C2, "c"] and r.conflicts == 1


def test_empty_base():
    assert merge3([], ["a"], ["b"]).lines == [C0, "a", C1, "b", C2]
    assert merge3([], ["a"], ["a"]) == (["a"], 0)
    assert merge3([], [], ["b"]) == (["b"], 0)


def test_multiple_conflicts_counted():
    base = ["1", "2", "3", "4", "5"]
    r = merge3(base, ["1", "A", "3", "B", "5"], ["1", "a", "3", "b", "5"])
    assert r.conflicts == 2
    assert r.lines == ["1", C0, "A", C1, "a", C2, "3", C0, "B", C1, "b", C2, "5"]


def test_inputs_not_modified():
    base, ours, theirs = ["a", "b"], ["a", "B"], ["A", "b"]
    merge3(base, ours, theirs)
    assert (base, ours, theirs) == (["a", "b"], ["a", "B"], ["A", "b"])


def test_symmetry_properties_random():
    rng = random.Random(21)
    for _ in range(200):
        base = [f"l{i}" for i in range(rng.randint(0, 12))]
        x = [l if rng.random() > 0.3 else l + "'" for l in base]
        if rng.random() < 0.5:
            x.insert(rng.randint(0, len(x)), "NEW")
        assert merge3(base, x, base) == (x, 0)
        assert merge3(base, base, x) == (x, 0)
        assert merge3(x, x, x) == (x, 0)
        assert merge3(base, x, x) == (x, 0)


def test_random_disjoint_edits_merge_without_conflict():
    rng = random.Random(5)
    for _ in range(300):
        n = 14
        base = [f"line{i}" for i in range(n)]
        # choose edit positions at least 3 apart so every edit has its own region
        spots = sorted(rng.sample(range(1, n - 1), 4))
        if any(b - a < 3 for a, b in zip(spots, spots[1:])):
            continue
        ours_spots, theirs_spots = spots[0::2], spots[1::2]
        ours, theirs, expected = list(base), list(base), list(base)

        def edit(lst, i, kind, tag):
            if kind == "replace":
                lst[i] = f"{tag}{i}"
            elif kind == "delete":
                lst[i] = None
            else:
                lst[i] = [lst[i], f"{tag}{i}+"]

        for i in ours_spots:
            k = rng.choice(["replace", "delete", "insert"])
            edit(ours, i, k, "O"); edit(expected, i, k, "O")
        for i in theirs_spots:
            k = rng.choice(["replace", "delete", "insert"])
            edit(theirs, i, k, "T"); edit(expected, i, k, "T")

        def flat(lst):
            out = []
            for x in lst:
                if x is None:
                    continue
                out.extend(x if isinstance(x, list) else [x])
            return out

        r = merge3(base, flat(ours), flat(theirs))
        assert r.conflicts == 0, (base, flat(ours), flat(theirs), r)
        assert r.lines == flat(expected)
