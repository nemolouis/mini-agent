# 05 · `miniagent/agent.py`:agent 主循环(核心)

整个项目最重要的文件。先看它想解决的问题,再逐行。

## 先理解"对话列表"

模型是**无状态**的:每次请求你都要把完整对话历史重新发过去。所以我们维护一个列表 `messages`,每一步往里追加:

```python
[
 {"role": "user",      "content": "修复 moving_average 的 bug"},          # 任务
 {"role": "assistant", "content": None,
  "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "grep", "arguments": "{\"pattern\":\"def\"}"}}]},  # 模型要求调工具
 {"role": "tool", "tool_call_id": "c1", "content": "stats.py:1:def moving_average..."},    # 我们执行后的结果
 {"role": "assistant", "content": "已修复,测试通过。"},                                     # 模型最终回答
]
```

三种角色:`user`(任务)、`assistant`(模型)、`tool`(工具结果)。`tool_call_id` 用来把"结果"和"哪次调用"对上号。

## 第 1–26 行:导入与两段提示词

- 第 4–8 行:`hashlib`(算哈希)、`json`、`time`、`dataclass, field`、`Callable`。
- 第 10–12 行:导入本项目的 `ModelResponse`、工具、轨迹。
- 第 14–21 行 `SYSTEM_PROMPT`:系统提示词,规定工作方式:先探索 → 提假设 → 最小修改 → 跑测试验证 → 不要改测试 → 最后只用文字总结。
  - 行尾的 `\` 在三引号字符串里表示"续行":下一行接在后面、不插入换行,只为了源码不太长。
- 第 23–26 行 `SUMMARY_PROMPT`:压缩上下文时,让模型写"进度摘要"的指令。

## 第 29–36 行:`RunResult`

一次运行的结果:`status`(`done` / `max_steps` / `length` / `error`)、步数、最终文本、总输入/输出 token、错误信息。

## 第 39–58 行:`Agent` 的字段

| 字段 | 含义 |
|---|---|
| `client` | 发请求的对象,只要有 `.chat()` 方法即可(便于测试替换) |
| `model` | 模型名 |
| `workspace` | 工作区(工具只能在里面操作) |
| `confirm` | 确认回调 `(工具名, 参数) -> bool`,默认一律同意 |
| `trajectory` | 日志对象,默认是不落盘的空日志 |
| `max_steps` | 最多循环几步,防止无限循环 |
| `max_tokens` | 单次回复最多多少 token |
| `context_limit` | 上下文预算,超过 70% 触发压缩 |
| `keep_recent` | 压缩时原样保留最近多少条消息 |
| `system` | 系统提示词 |
| `temperature` | 随机性(评测时固定) |
| `disabled_tools` | 要禁用的工具名(用来做消融实验) |
| `meta` | 附加信息,写进 `run_start`(如任务 id) |

两个值得说的写法:
- 第 44 行 `confirm: ... = lambda name, args: True`:默认值是个匿名函数,恒返回 `True`(自动同意)。
- 第 45、53 行 `field(default_factory=...)`:**可变对象(字典、自定义对象)不能直接当默认值**,否则所有实例会共享同一个。`default_factory` 表示"每创建一个实例,就调用一次这个函数生成新的"。

**第 55–58 行 `__post_init__`**:dataclass 自动生成 `__init__` 之后会自动调它。这里构造 `self.tools`:`build_tools(...)` 得到全部工具,字典推导过滤掉 `disabled_tools` 里的。

## 第 61–111 行:`run()` —— 主循环

```python
def run(self, task: str) -> RunResult:
```

**准备阶段(62–73 行)**
- 第 62 行:`messages` 初始只有用户的任务。
- 第 63–68 行:写 `run_start` 事件,配置里包括 `system_sha1`——系统提示词的哈希前 12 位,这样评测里不同提示词版本可以被区分,又不用把全文写进每份日志。
- 第 69 行 `in_tok = out_tok = 0`:链式赋值,两个变量都置 0。
- 第 70 行 `last_input`:最近一次调用的输入 token 数,用来判断是否该压缩。
- 第 72 行 `status = "max_steps"`:默认状态。如果循环自然跑满、没有被 `break`,就保持这个值。

**循环(74–103 行)**
- 第 75 行 `for step in range(1, self.max_steps + 1)`:从第 1 步到第 `max_steps` 步。
- 第 76–78 行:如果上一步的输入 token 超过预算的 70% → `_compact` 压缩消息列表,并清零 `last_input`。
- 第 80–85 行:调用模型,传入模型名、token 上限、系统提示词、工具说明书列表(`[t.spec() for t in self.tools.values()]`)、消息、temperature。`time.time()` 前后相减得到延迟。
- 第 86 行:把每个 `ToolCall` 解析成字典(见 `_parse_call`)。
- 第 87–89 行:累计 token。注意 `in_tok` 是**每一步输入的总和**,因为每步都重发整个历史,所以它体现的是总计费量,不是上下文长度。
- 第 90–95 行:写 `model_call` 事件。
- 第 96 行:把模型回复追加进 `messages`(格式由 `_assistant_message` 构造)。
- 第 97 行:记下最新一次的文本,最后一次就是最终回答。
- 第 99–102 行:**核心判断**
  - 模型要调工具 → 逐个执行,把每个 `tool` 消息追加进去(`messages.extend(生成器)`),然后 `continue` 进入下一轮;
  - 没有工具调用 → 说明模型认为做完了:`finish_reason == "stop"` 记为 `done`,否则记原因(如 `length`),然后 `break`。

**异常处理(104–107 行)**
`except Exception` 兜住 API 失败等任何意外:写一条 `run_end(status="error")`,返回带错误的 `RunResult`,不让异常抛出去弄坏整批评测。

**收尾(109–111 行)**
正常结束写 `run_end` 并返回结果。

## 第 114–138 行:`_run_tool` —— 执行一次工具调用

```python
name, args = call["name"], call["input"]
approved, is_error = True, False
tool = self.tools.get(name)
```

四种情形,按优先级:
1. **工具不存在**(第 119–120 行):模型编了个不存在的工具名 → 把"unknown tool"作为错误回传。
2. **参数不是合法 JSON**(121–122 行):`_parse_call` 标记了 `parse_error` → 回传错误。
3. **需要确认但用户拒绝**(124–125 行):`approved=False`,并告诉模型"换个办法或解释为什么需要"。
4. **正常执行**(126–134 行):`tool.func(args)`,按异常类型分三层捕获:
   - `ToolError`:工具自己抛的"预期内错误"(如路径越界、没匹配到)。
   - `KeyError / TypeError / ValueError`:通常是模型传错了参数(缺字段、类型不对)。
   - 其它 `Exception`:工具自身的 bug,也不允许让整个运行崩溃。
   - **except 的顺序是"从具体到宽泛"**,因为 Python 按顺序匹配,第一个匹配的生效。

不管哪种结果,都在第 135–137 行写 `tool_result` 事件,第 138 行返回 `{"role": "tool", "tool_call_id": ..., "content": out}`。

核心思想:**所有错误都变成文字回传给模型**,模型看到后常常会自己修正。这是 agent 稳健性的关键。

## 第 141–172 行:`_compact` —— 上下文压缩

触发条件见主循环。分两个阶段,**能便宜解决就不做贵的**:

**阶段 1:抹掉旧的工具输出(143–153 行)**
- 第 144 行 `cutoff = max(len(messages) - self.keep_recent, 1)`:最近 `keep_recent` 条不动,更早的才处理;至少从 1 开始(下标 0 是原始任务,永远不动)。
- 第 145 行 `out = [m for m in messages]`:复制一份新列表(浅拷贝),修改不影响原列表。
- 第 146–149 行:对更早的消息,若是 `tool` 消息且内容超过 200 字,替换成 `[elided N chars]`。`{**m, "content": ...}` 是"复制字典并覆盖一个键"。
- 第 150–153 行:估算压缩后的大小并记日志;如果已不超过预算的 50%,直接返回。

**阶段 2:让模型总结中间部分(155–171 行)**
- 第 157–159 行:确定保留尾部的起点 `i`,并往后移动直到遇到一条 `assistant` 消息。
  - 原因:尾部若以 `tool` 消息开头,它对应的 `assistant`(带 `tool_calls`)就被丢掉了,API 会报错。让尾部从 `assistant` 开始,调用与结果成对保留。
- 第 160–161 行:找不到合适切点就放弃总结,返回阶段 1 的结果。
- 第 162 行:`transcript = _render(messages[1:i])`——注意用的是**未抹掉**的原始 `messages`,注释写明"抹掉不能饿死摘要"。如果用被抹掉的版本,摘要里就丢了关键内容(这是项目里发现并修复过的真实缺陷,有回归测试)。
- 第 163–166 行:调用模型生成摘要,不带工具、不带系统提示词,`max_tokens=1500`。
- 第 168 行:新的第一条用户消息 = 原始任务 + `[Progress so far...]` + 摘要。
- 第 169 行 `new = [head] + out[i:]`:新对话 = 摘要头 + 保留的尾部。
- 第 170–172 行:写日志并返回。

## 第 175–211 行:辅助函数

**`_parse_call(c)`(176–183 行)**:把模型给的 `arguments` 字符串解析成字典。
- 解析失败(`json.loads` 抛 `ValueError`,`JSONDecodeError` 是它的子类)或解析出来不是字典 → 返回 `parse_error` 标记,原始字符串存在 `_raw_arguments` 里便于排查。
- 第 179–180 行 `if not isinstance(args, dict): raise ValueError(...)` 是主动抛异常,让它走同一个 `except`。

**`_assistant_message(resp)`(186–192 行)**:把 `ModelResponse` 转回 API 要求的 assistant 消息。`content` 为空时用 `None`;有工具调用才加 `tool_calls`(原样回放 `arguments` 字符串)。

**`_estimate_tokens(messages)`(195–196 行)**:粗略估计 token 数:整个对话序列化成 JSON 后字符数 `// 3`。不精确,但压缩阶段不需要精确。

**`_render(messages)`(199–211 行)**:把一段消息渲染成给摘要模型看的纯文本:
- `tool` 消息 → `[result] 内容前500字`。
- 有文本 → `[角色] 文本`。
- 有工具调用 → `[call 工具名] 参数前500字`。
- `m.get("tool_calls") or []` 防 `None`。

## 把整个流程串起来

```
run() ──循环──▶ client.chat() ──▶ 模型回复
                   │
        有 tool_calls?──是──▶ _run_tool() ×N ──▶ 追加 tool 消息 ──▶ 下一轮
                   │
                   否──▶ done / length,结束
每轮开头:上下文 > 70%? ──是──▶ _compact()
```
