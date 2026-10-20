# 逐行讲解:总览与 Python 速查

面向"只会 Python 基础语法"的读者。每个 `.py` 文件一份讲解,按**从简单到复杂、从底层到上层**的顺序排列。

## 阅读顺序

| 顺序 | 文件 | 一句话 | 讲解 |
|---|---|---|---|
| 1 | `miniagent/safety.py` | 危险命令黑名单(25 行) | [01-safety.md](01-safety.md) |
| 2 | `miniagent/trajectory.py` | 把运行过程一行行写进日志文件 | [02-trajectory.md](02-trajectory.md) |
| 3 | `miniagent/tools.py` | agent 的"手":读/写/改文件、跑命令、搜索 | [03-tools.md](03-tools.md) |
| 4 | `miniagent/client.py` | 通过 HTTP 跟 DeepSeek 对话 | [04-client.md](04-client.md) |
| 5 | `miniagent/agent.py` | **核心**:agent 主循环 + 上下文压缩 | [05-agent.md](05-agent.md) |
| 6 | `miniagent/cli.py` | 命令行入口 | [06-cli.md](06-cli.md) |
| 7 | `miniagent/eval/tasks.py` | 任务加载、dev/test 划分、哈希防篡改 | [07-eval-tasks.md](07-eval-tasks.md) |
| 8 | `miniagent/eval/grade.py` | 判分、防作弊、失败归因 | [08-eval-grade.md](08-eval-grade.md) |
| 9 | `miniagent/eval/runner.py` | 跑一次"任务×配置×重复" | [09-eval-runner.md](09-eval-runner.md) |
| 10 | `miniagent/eval/report.py` | 统计、置信区间、报告、对比 | [10-eval-report.md](10-eval-report.md) |
| 11 | `miniagent/eval/cli.py`、`eval/__main__.py` | 评测命令行 | [11-eval-cli.md](11-eval-cli.md) |
| 12 | `tests/*.py` | 测试 | [12-tests.md](12-tests.md) |

`__init__.py`(两个,都是空文件):告诉 Python"这个文件夹是一个包(package)",才能写 `from miniagent.agent import Agent`。

## 文件之间的依赖关系

```
cli.py ──▶ agent.py ──▶ client.py      (和模型说话)
              │   ├───▶ tools.py ──▶ safety.py   (干活 + 拦截危险命令)
              │   └───▶ trajectory.py            (写日志)
eval/cli.py ─▶ eval/runner.py ─▶ agent.py
                  ├─▶ eval/grade.py   (判分)
                  └─▶ eval/tasks.py   (任务)
eval/cli.py ─▶ eval/report.py         (统计)
```

箭头方向 = "import 了谁 / 用到了谁"。越靠右越底层。

## Python 速查(讲解里会反复出现)

**f-string**:`f"hello {name}"` 把变量嵌进字符串。`{x:.2f}` 表示保留 2 位小数,`{i:>6}` 表示右对齐占 6 格。

**类型标注**:`def f(a: int, b: str = "x") -> bool:` 里的 `: int`、`-> bool` 只是给人和工具看的"提示",**运行时不检查**。`str | None` 读作"字符串或 None"。`list[dict]` 是"元素为字典的列表"。

**`from __future__ import annotations`**:让类型标注不在定义时立即求值,这样 `str | Path | None` 这类写法在旧版 Python 上也不报错。可以当作"类型标注的兼容咒语"。

**`@dataclass`**:装饰器。你只写字段名和类型,Python 自动帮你生成 `__init__`、`__repr__` 等。

```python
@dataclass
class P:
    x: int
    y: int = 0      # 带默认值
P(1)  # 等价于 P(x=1, y=0)
```

**`*args` 与 `**kwargs`**:
- 定义函数时 `def log(event, **data)`:把多余的"关键字参数"收集成字典 `data`。
- 调用/构造时 `{**a, "k": 1}`:把字典 `a` 展开,再覆盖/追加键。`[*a, *b]` 同理展开列表。

**关键字参数强制**:函数参数里单独一个 `*`,如 `def chat(self, *, model, messages)`,表示它后面的参数**只能用 `名字=值` 的形式传**。

**推导式**:
```python
[x * 2 for x in xs if x > 0]        # 列表推导
{k: v for k, v in pairs}            # 字典推导
{x for x in xs}                     # 集合推导
(x for x in xs)                     # 生成器表达式:惰性,用到才算
sum(1 for x in xs if cond)          # 常见用法:数满足条件的个数
```

**`with`**:自动收尾的语法。`with open(p) as f:` 块结束时自动关文件;`with tempfile.TemporaryDirectory() as d:` 结束时自动删临时目录。

**异常**:`try: ... except SomeError as e: ...`;`raise X(...)` 主动抛出;自定义异常只要 `class MyErr(Exception): pass`。

**`or` 的"取默认值"用法**:`a or b` 在 `a` 为假值(`None`、`""`、`0`、`[]`、`{}`)时返回 `b`。如 `args.get("path") or ""`。

**`dict.get(key, default)`**:取不到不报错,返回默认值;`d[key]` 取不到会抛 `KeyError`。

**切片**:`s[:5]` 前 5 个;`s[-5:]` 最后 5 个;`s[a:b]` 下标 a 到 b-1。

**`Path`(pathlib)**:把路径当对象用。`p / "sub"` 拼路径;`p.read_text()` 读文件;`p.parent` 上级目录;`p.rglob("*.py")` 递归找文件。

**正则 `re`**:描述"一类字符串"的小语言。`re.compile(p)` 预编译,`.search(s)` 在字符串任意位置找匹配。

**JSON**:`json.dumps(obj)` 对象→字符串;`json.loads(s)` 字符串→对象。

**两个约定**:
- 以下划线开头的名字(`_DENY`、`_run_tool`)表示"内部使用,别从外面调"。
- `if __name__ == "__main__":` 只在"直接运行这个文件"时才执行,被别的文件 import 时不执行。
