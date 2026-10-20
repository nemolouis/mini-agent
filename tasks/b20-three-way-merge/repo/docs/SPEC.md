# Three-way line merge

`merge3(base, ours, theirs)` takes three lists of lines (strings without newlines) and returns
`MergeResult(lines, conflicts)`.

## Algorithm (diff3 style)
1. Align `base` with `ours` and `base` with `theirs` using longest common subsequences.
   (When several LCS alignments exist, which one is used is unspecified; tests avoid that.)
2. A base line that is matched in BOTH alignments is a *sync point*. Sync points split the
   three sequences into aligned *regions*: the lines of base, ours and theirs strictly
   between two consecutive sync points (or before the first / after the last one).
3. For each region with segments `b`, `o`, `t`:
   - if `o == b` take `t`;
   - else if `t == b` take `o`;
   - else if `o == t` take `o` (both sides made the same change);
   - else it is a **conflict**: emit
         <<<<<<< ours
         (the lines of o)
         =======
         (the lines of t)
         >>>>>>> theirs
     and count one conflict.
4. Sync point lines are copied through unchanged between regions.

Note that changes in the same region conflict even if they touch different lines
(ours edits line 2 while theirs inserts after line 2 inside the same region).
`conflicts` is the number of conflict blocks. The inputs are never modified.
