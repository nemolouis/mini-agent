# 02 · `miniagent/trajectory.py`:轨迹日志

**作用**:把一次运行里发生的每件事,以"一行一个 JSON"的格式追加写入文件(JSONL)。评测和回放都靠它。

## 为什么用 JSONL

- 每行是独立 JSON,**追加写**即可,运行到一半崩溃,已写的部分仍然完整。
- 读取时 `for line in file: json.loads(line)` 就行。

## 逐行

**第 1–16 行**:docstring,列出了所有事件类型及字段:

| 事件 | 何时写 | 主要字段 |
|---|---|---|
| `run_start` | 开始 | task、model、config |
| `model_call` | 每次调用模型 | step、耗时、finish_reason、text、tool_calls、usage |
| `tool_result` | 每次工具执行完 | tool_call_id、name、input、output、is_error、approved |
| `compaction` | 压缩上下文 | kind(elide/summary)、前后 token 估计 |
| `run_end` | 结束 | status、steps、token 汇总、final_text |

**第 17 行** `from __future__ import annotations`:见总览速查。

**第 19–21 行**:导入 `json`(序列化)、`time`(时间戳)、`Path`(路径对象)。

**第 24 行** `class Trajectory:`:定义一个类,`Trajectory` 的实例代表"一次运行的日志"。

**第 25–30 行** `__init__`(构造函数,创建对象时自动执行):
- `run_dir: str | Path | None`:可以传字符串、Path,或者 `None`。
- 第 26 行 `self.path: Path | None = None`:先假设"不写日志"。`self.xxx` 是挂在这个对象上的属性。
- 第 27 行 `if run_dir is not None:`:传了目录才真正启用。
- 第 28 行 `d = Path(run_dir)`:统一成 Path 对象。
- 第 29 行 `d.mkdir(parents=True, exist_ok=True)`:创建目录;`parents=True` 连同缺失的上级目录一起建;`exist_ok=True` 已存在也不报错。
- 第 30 行 `self.path = d / "trajectory.jsonl"`:日志文件路径。

**第 32–37 行** `log(self, event, **data)`:

- `**data` 把调用时额外的关键字参数收成字典。比如 `log("run_end", status="done", steps=5)` 里,`data == {"status": "done", "steps": 5}`。
- 第 33–34 行:`path` 是 `None` 就什么都不做直接返回(用于测试或不想落盘时)。这是一种"空对象"写法:调用方永远可以放心调用 `log`,不用每次判断。
- 第 35 行 `rec = {"ts": round(time.time(), 3), "event": event, **data}`:构造一条记录。`time.time()` 是 Unix 时间戳,`round(..., 3)` 保留三位小数;`**data` 把额外字段展开进来。
- 第 36 行 `with self.path.open("a", encoding="utf-8") as f:`:以**追加模式**(`"a"`)打开文件,块结束自动关闭。
- 第 37 行 `f.write(json.dumps(rec, ensure_ascii=False) + "\n")`:转成 JSON 字符串并加换行。`ensure_ascii=False` 让中文保持原样,不变成 `中` 这种转义。

## 使用方

`agent.py` 里 `self.trajectory.log("model_call", step=step, ...)`;评测在 `runner.py` 里创建 `Trajectory(traj_dir)` 并在运行后读回。
