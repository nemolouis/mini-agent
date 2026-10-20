# 06 · `miniagent/cli.py`:命令行入口

**作用**:把 `miniagent "任务" -w 仓库` 这样的命令行,变成对 `Agent.run()` 的调用。

## 第 1–11 行

- `argparse`:标准库,解析命令行参数。
- `sys`:访问标准错误输出、退出码。
- `from .agent import Agent` 等:导入本项目模块(前面的 `.` 表示同一个包)。
- 第 11 行 `DEFAULT_MODEL = "deepseek-chat"`:默认模型名。

## 第 14–27 行:`_make_confirm` —— 用户确认逻辑

```python
def _make_confirm(auto: bool):
    approve_all = auto

    def confirm(name, args) -> bool:
        nonlocal approve_all
        ...
    return confirm
```

这是**闭包**:函数里定义函数,内层函数能"记住"外层的变量。
- 外层接收 `auto`(是否带了 `-y`),保存为 `approve_all`。
- 返回的 `confirm` 每次被调用时:
  - 第 19–20 行:已经全部同意 → 直接 `True`。
  - 第 21 行 `shown = args.get("command") or args.get("path") or ""`:展示给用户看的内容——命令或路径。
  - 第 22 行 `input(...)`:在终端询问 `[y]es / [n]o / [a]ll`。
  - 第 23–24 行:选 `a`(全部同意)就把 `approve_all` 设为 `True`,之后不再询问。
  - 第 25 行 `return ans in ("y", "a")`:返回布尔值。
- `nonlocal approve_all`(第 18 行):内层函数要**修改**外层变量必须声明,否则会被当成新的局部变量。

## 第 30–61 行:`main`

**参数定义(31–42 行)**:
- `ArgumentParser(prog="miniagent")`:解析器。
- `ap.add_argument("task", ...)`:不带 `-` 的是**位置参数**,必填,即任务描述。
- `-w/--workspace`:agent 可操作的仓库根目录,默认当前目录。
- `-m/--model`:模型名。
- `--max-steps`:最大步数,`type=int` 自动转整数。
- `-y/--yes`:`action="store_true"` 表示出现这个开关就为 `True`。
- `--context-limit`、`--keep-recent`、`--temperature`、`--runs-dir`:对应 `Agent` 的字段。
  - 第 38 行帮助文字里 `70%%` 是因为 argparse 的帮助会做 `%` 格式化,`%%` 才是字面的 `%`。
- 第 42 行 `args = ap.parse_args(argv)`:解析。`argv=None` 时读真实的命令行;测试里可以传列表。

**创建客户端(44–48 行)**:
`ChatClient()` 在缺 API key 时抛 `APIError` → 向**标准错误**打印并 `return 2`(约定:2 表示用法/配置错误)。

**创建并运行(50–57 行)**:
- 第 50 行 `time.strftime("%Y%m%d-%H%M%S")` 生成如 `20261011-154130` 的时间戳,作为本次运行目录名。
- 第 51–56 行:构造 `Agent`,把命令行参数一一对应进去。
- 第 57 行 `res = agent.run(args.task)`。

**输出(58–61 行)**:打印状态、步数、token、最终文本和日志路径;`return 0 if res.status == "done" else 1`,成功返回 0,否则 1(Shell 里据此判断成功与否,`run_task.sh` 就会用到)。

**第 64–65 行**:
```python
if __name__ == "__main__":
    sys.exit(main())
```
直接 `python miniagent/cli.py` 运行时才执行。通过 `pyproject.toml` 里 `miniagent = "miniagent.cli:main"` 安装后,`miniagent` 命令就是直接调用 `main`。
