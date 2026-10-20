# CSV loader specification

`load(path, schema=None)` returns a list of dicts, one per data row.

## Input
- UTF-8 text, with or without a byte-order mark (BOM). The BOM is not part of the data.
- Rows end with `\n` or `\r\n`. Fields follow RFC 4180 quoting: a quoted field may contain
  commas, line breaks and doubled quotes (`""` is one `"`).
- Rows in which every cell is empty (blank lines) are skipped.

## Headers (first row)
- Surrounding whitespace is stripped, text is lower-cased, and runs of whitespace inside a
  header become a single `_`: `" Unit Price "` -> `unit_price`.
- An empty header becomes `column_N` where N is its 1-based position.
- If a name occurs more than once, the first keeps its name and later ones get the
  suffixes `_2`, `_3`, ... in order of appearance.

## Cells
- Surrounding whitespace of every cell is stripped (also inside quotes).
- A row with fewer cells than headers has `None` for the missing ones.
  A row with more cells than headers raises `ValueError`.

## Types (`schema` maps normalized header -> "str" | "int" | "float" | "bool")
- Columns not in the schema are `"str"`. `"str"` cells are returned as-is (empty string stays "").
- For other types an empty cell becomes `None`.
- `"bool"` accepts (case-insensitive) true/yes/y/1 and false/no/n/0; anything else raises `ValueError`.
- `"int"` and `"float"` use the usual conversions and raise `ValueError` on bad input.
