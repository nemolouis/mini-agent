# 03 · `miniagent/tools.py`:agent 的"手"

**作用**:实现 5 个工具(`read_file` / `write_file` / `edit_file` / `bash` / `grep`),以及把它们描述给模型看的 JSON 说明书。

约定(第 3–5 行):每个工具接收一个字典(模型给出的参数),返回一个字符串(给模型看的结果)。出错就抛 `ToolError`,由 `agent.py` 转成错误信息回传给模型,让它自己调整,而不是让整个程序崩溃。

## 第 1–19 行:导入和常量

- 第 9–14 行:`os`(环境变量)、`re`(正则)、`subprocess`(执行外部命令)、`dataclass`、`Path`、`Callable`(表示"可调用对象"的类型)。
- 第 16 行 `from .safety import check_command`:开头的 `.` 表示"同一个包里的",即 `miniagent/safety.py`。
- 第 18 行 `MAX_OUTPUT_CHARS = 20_000`:数字里的下划线只是为了好读,等于 20000。输出超过这个长度会被截断,避免一次工具输出把上下文撑爆。
- 第 19 行 `SKIP_DIRS = {...}`:大括号里是逗号分隔的元素 → 这是**集合**(set)。`grep` 时跳过这些目录。

## 第 22–23 行:`ToolError`

`class ToolError(Exception): pass`:自定义异常类,什么都不加,只是为了有个专属名字让别的代码能 `except ToolError`。

## 第 26–30 行:`truncate`

保留头尾、砍掉中间:
- 第 27–28 行:不超长就原样返回。
- 第 29 行 `half = limit // 2`:`//` 是整除。
- 第 30 行:`text[:half]` 前半 + 提示 + `text[-half:]` 后半。头尾都保留,是因为命令输出的开头(命令回显)和结尾(报错/结果)通常最重要。

## 第 33–43 行:`Tool` 数据类

一个工具由 5 个字段描述:
- `name`:工具名。
- `description`:给模型看的说明(模型靠它决定何时用)。
- `input_schema`:参数的 JSON Schema(告诉模型要传哪些参数、什么类型)。
- `func: Callable[[dict], str]`:真正执行的函数,参数是 dict,返回 str。
- `needs_confirm: bool = False`:是否要用户确认。

`spec()` 方法(第 41–43 行)按 OpenAI 兼容接口要求的格式组装工具说明书:`{"type":"function","function":{name, description, parameters}}`。这就是请求里 `tools=[...]` 的一项。

## 第 46–56 行:`Workspace`(工作区)

**`__init__`(47–50 行)**
- `Path(root).resolve()`:转成**绝对路径**,并消除 `..`、解析符号链接。
- 不是目录就 `raise ValueError`。

**`resolve(path)`(52–56 行)——最重要的安全函数**
- 第 53 行 `p = (self.root / path).resolve()`:把模型给的相对路径拼到工作区根上再规范化。
- 第 54 行:`p != self.root and self.root not in p.parents` 意思是:既不是根本身,也不在根的子孙里 → 越界。`p.parents` 是 `p` 的所有祖先目录。
- 例:`../../etc/passwd` 规范化后是 `/etc/passwd`,不在根下面 → 抛 `ToolError`。
- 即使模型给绝对路径 `/etc/passwd`,`root / "/etc/passwd"` 在 pathlib 里结果就是 `/etc/passwd`,同样被拦住。

## 第 59–73 行:`read_file`

1. 第 60–62 行:解析路径,不是文件就报错。
2. 第 63 行 `offset = max(int(args.get("offset", 1)), 1)`:起始行号,默认 1,且不小于 1。`int(...)` 是因为模型有时会传字符串 `"5"`。
3. 第 64 行 `limit`:最多读几行,默认 2000。
4. 第 65–68 行:读文本并按行拆分;文件不是 UTF-8(如二进制)就抛 `ToolError`。
5. 第 69 行 `lines[offset - 1 : offset - 1 + limit]`:列表下标从 0 开始,而行号从 1 开始,所以减 1。
6. 第 70 行:`enumerate(chunk, start=offset)` 给每行配上行号;`f"{i:>6}\t{l}"` 行号右对齐占 6 格 + 制表符 + 行内容。再用 `"\n".join(...)` 拼回一个字符串。
7. 第 71–72 行:如果后面还有内容,附一句提示"还有 N 行,用 offset 继续读"。
8. 第 73 行 `return truncate(out) or "(empty file)"`:空字符串是假值,所以空文件返回 `"(empty file)"`。

## 第 75–79 行:`write_file`

- `p.parent.mkdir(parents=True, exist_ok=True)`:确保上级目录存在。
- `p.write_text(...)`:写入(覆盖)。
- 返回一句"写了多少字符",给模型确认。

## 第 81–95 行:`edit_file`

要求 `old_string` 在文件里**恰好出现一次**,这样不会改错地方,也强迫模型写出足够的上下文:
- 第 85 行 `old, new = args["old_string"], args["new_string"]`:一行同时给两个变量赋值。
- 第 86–87 行:新旧相同,报错(没有意义的编辑)。
- 第 89 行 `n = text.count(old)`:统计出现次数。
- 第 90–93 行:0 次 → "没找到"(提示要完全匹配含空白);多次 → "出现了 n 处,请加更多上下文"。
- 第 94 行 `text.replace(old, new, 1)`:最多替换 1 次。

## 第 97–110 行:`bash`

1. 第 99–101 行:先过黑名单,命中就抛 `ToolError`。
2. 第 102 行 `timeout = min(int(args.get("timeout", 60)), 300)`:默认 60 秒,最多 300 秒。
3. 第 104–107 行 `subprocess.run(...)`:
   - `cmd, shell=True`:交给系统 shell 解析,所以管道、`&&` 都能用(同时也是风险所在)。
   - `cwd=self.root`:在工作区根目录执行。
   - `capture_output=True, text=True`:把 stdout/stderr 收集成字符串。
   - `env={**os.environ, "GIT_PAGER": "cat", "PAGER": "cat"}`:复制当前环境变量并追加两项,避免 `git log` 之类进入交互式分页器卡住。
4. 第 108–109 行:超时抛 `subprocess.TimeoutExpired`,转成 `ToolError`。
5. 第 110 行:返回 `exit code: N` + stdout + stderr,`rstrip()` 去掉末尾空白,再 `truncate`。

## 第 112–133 行:`grep`

1. 第 113–116 行:编译正则,写错了就给模型一个明确的错误。
2. 第 117 行:搜索起点,默认当前工作区根 `"."`,同样要过 `resolve`。
3. 第 119–122 行 `files = ...`:
   - 如果起点本身是文件,就只搜它(`[base]`)。
   - 否则是一个**生成器表达式**:`base.rglob(glob or "*")` 递归列出文件(`glob` 如 `*.py`),`sorted` 保证顺序稳定;条件是"是文件,且路径的任何一段都不在 `SKIP_DIRS` 里"。`SKIP_DIRS & set(...)` 是集合交集,非空即真。
4. 第 123–132 行:逐文件逐行匹配,命中就记录 `相对路径:行号:行内容(最多300字)`;累计 200 条就提前返回;读不了的文件(`UnicodeDecodeError`、`OSError`)`continue` 跳过。
5. 第 133 行:没有命中返回 `"no matches"`。

## 第 136–156 行:`build_tools`

这里有一个小技巧:

```python
S = lambda **props: {"type": "object", "properties": props,
                     "required": [k for k, v in props.items() if not v.pop("optional", False)]}
```

- `lambda` 是匿名函数,这里被赋给名字 `S`,用来快速生成参数 schema。
- `**props` 收集所有关键字参数为字典,如 `S(path={"type":"string"}, offset={..., "optional": True})`。
- `required` 列表:遍历每个参数,`v.pop("optional", False)` 把 `"optional"` 这个自定义标记取出并**从字典里删掉**(这样不会泄露到发给模型的 schema),返回它的值;不是可选的才放进 `required`。

之后创建 5 个 `Tool(...)`:
- 前三个位置参数是 `name, description, input_schema`,第四个是实际函数 `ws.read_file`(注意**没有括号**,传的是函数本身,不是调用结果)。
- `write_file` / `edit_file` / `bash` 设了 `needs_confirm=True`,这些会改动环境的操作需要确认;`read_file` / `grep` 只读,不需要。

最后 `return {t.name: t for t in tools}`:字典推导,得到 `{"read_file": Tool(...), ...}`,`agent.py` 用工具名就能查到对应工具。
