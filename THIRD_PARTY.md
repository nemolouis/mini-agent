# Third-party material

mini-agent itself is MIT-licensed (see `LICENSE`). The repository also contains source code of the open-source libraries
below. It is used as *seed libraries* for the task generator: `seeds/<name>/repo/` holds the library with its own tests, and
the generated tasks (`gen_tasks/`, not committed, see `gen_tasks/README.md`) hold the same code with one injected bug. The
license text of each library is kept next to its code (`seeds/<name>/repo/<license file>`) and applies to that code, not to
the rest of this repository.

| package | version | license | copyright line from its license file | license file | sdist sha256 |
|---|---|---|---|---|---|
| boltons | 26.2.0 | BSD (2-clause text) | Copyright (c) 2013, Mahmoud Hashemi | `LICENSE` | `d39cfd15c1a1c3bd…` |
| cachetools | 7.2.3 | MIT | Copyright (c) 2014-2026 Thomas Kemmer | `LICENSE` | `e6fafd06de4a5bd9…` |
| colorama | 0.4.6 | BSD (3-clause text) | Copyright (c) 2010 Jonathan Hartley | `LICENSE.txt` | `08695f5cb7ed6e05…` |
| decorator | 5.3.1 | BSD (2-clause text) | Copyright (c) 2005-2026, Michele Simionato | `LICENSE.txt` | `4cbcdd55a6efadb9…` |
| inflection | 0.5.1 | MIT | Copyright (C) 2012-2020 Janne Vanhala | `LICENSE` | `1a29730d366e996a…` |
| ordered-set | 4.1.0 | MIT | Copyright (c) 2012-2022 Elia Robyn Lake | `MIT-LICENSE` | `694a8e44c87657c5…` |
| parse | 1.22.3 | MIT | Copyright (c) 2012-2019 Richard Jones <richard@python.org> | `LICENSE` | `7e79bb39c72c3bf1…` |
| schema | 0.7.8 | MIT | Copyright (c) 2012 Vladimir Keleshev, <vladimir@keleshev.com> | `LICENSE-MIT` | `e86cc08edd6fe6e2…` |
| six | 1.17.0 | MIT | Copyright (c) 2010-2024 Benjamin Peterson | `LICENSE` | `ff70335d468e7eb6…` |
| sqlparse | 0.6.0 | BSD (3-clause text) | Copyright (c) 2016, Andi Albrecht <albrecht.andi@gmail.com> | `LICENSE` | `113c35c75365ab9c…` |
| tabulate | 0.10.0 | MIT | Copyright (c) 2011-2020 Sergey Astanin and contributors | `LICENSE` | `e2cfde8f79420f6d…` |
| termcolor | 3.3.0 | MIT | Copyright (c) 2008-2011 Volvox Development Team | `COPYING.txt` | `348871ca648ec6a9…` |
| toolz | 1.2.0 | BSD (3-clause text) | Copyright (c) 2013 Matthew Rocklin | `LICENSE.txt` | `9667a038e9d6ecba…` |
| xmltodict | 1.0.4 | MIT | Copyright (C) 2012 Martin Blech and individual contributors. | `LICENSE` | `6d94c9f834dd9e44…` |

Notes
- Source: the source distribution (sdist) of the exact release, downloaded from PyPI (`files.pythonhosted.org`), checked against
  the sha256 PyPI publishes, and unpacked without executing anything. The full list with URLs is `seeds/SOURCES.json`
  (`scripts/fetch_seeds.py`, `scripts/make_seeds.py`).
- What was changed: only files were left out or added. Test files that do not pass in the sandbox were removed, `docs`/packaging
  files were not copied, and a one-line `pytest.ini` was added to `decorator`. The library code itself is unmodified in
  `seeds/`; in the generated tasks one operator, constant or statement is changed on purpose.
- Downloaded and then discarded (not included, their tests did not run in the sandbox or were missing): jmespath, jsonpointer, more-itertools, pytimeparse, sortedcontainers, toposort.
- `textkit` and `seqtools` in `seeds/` were written for this project (MIT).
- Not included here and obtained separately by the user: the model `Qwen/Qwen2.5-Coder-1.5B-Instruct` (Apache-2.0) and the
  Python packages installed from PyPI (`mlx-lm` and its dependencies) for training.
- Model outputs: trajectories in `results/` and `data/` were produced by third-party models (DeepSeek, Google Gemini, Zhipu GLM);
  the repository does not redistribute raw trajectories (see `.gitignore`). Check each provider's terms before publishing any.
