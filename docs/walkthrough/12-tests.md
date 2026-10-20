# 12 · `tests/`:测试

运行方式:`pytest -q`(在项目根目录)。**所有测试都不联网**:用"假客户端"代替真实模型。

## pytest 极简入门

- 文件名 `test_*.py`、函数名 `test_*` 会被自动发现并运行。
- 用普通的 `assert 条件` 断言;不满足就报失败并显示两边的值。
- 函数参数里写 `tmp_path`:pytest 会自动注入一个**独立的临时目录**(每个测试一个)。
- `with pytest.raises(X):` 断言"这段代码必须抛出 X 异常"。
- `@pytest.mark.parametrize("cmd", [...])` 让同一个测试用多组输入各跑一遍。
- `@pytest.fixture` 定义可复用的准备工作,测试函数把它的名字写进参数就会拿到。

## 假客户端的思路

真实模型每次回复不可控。测试里写一个"剧本":`script = [第1次回复, 第2次回复, ...]`,假客户端每次 `chat()` 就弹出下一条。这样可以精确构造"模型先调工具、再说完成"之类场景,验证 agent 循环的行为。

回复的写法(各测试文件里都有的两个小函数):
```python
def text(t): return t                                            # 一段文字
def call(i, name, **inp): return ToolCall(i, name, json.dumps(inp))  # 一次工具调用
```
`**inp` 收集关键字参数为字典,再 `json.dumps` 成字符串——模拟模型真实输出的"arguments 是 JSON 字符串"。

## `tests/test_safety_and_tools.py`

| 测试 | 验证 |
|---|---|
| `test_blocked`(参数化) | 9 条危险命令都被 `check_command` 拦住 |
| `test_allowed`(参数化) | `pytest -q`、`rm -rf build/`、`git status` 等正常命令不被误伤 |
| `test_path_escape` | `../../etc/passwd` 抛 `ToolError` |
| `test_write_read_edit` | 写入 → 读取 → 编辑 → 再读取,一条完整链路 |
| `test_edit_requires_unique` | `old_string` 出现多次或不存在,都必须报错 |
| `test_bash_and_block` | 正常命令得到 `exit code: 0`;`sudo` 被拦;`sleep 5` 在 1 秒超时下报错 |
| `test_grep` | 能搜到 `def foo`;无匹配返回 `"no matches"` |

`ws` 这个 fixture 创建绑定在临时目录上的 `Workspace`,让多个测试共用。

## `tests/test_client.py`

- `test_requires_api_key`:用 `monkeypatch.delenv` 临时删掉环境变量,期望 `ChatClient()` 抛 `APIError`。
- `test_parses_response_and_builds_request`:`monkeypatch.setattr(c, "_post", fake_post)` 把真正发网络请求的 `_post` 换成假函数。假函数记录收到的路径与请求体,并返回一份模拟的 API 响应。断言:请求发往 `/chat/completions`;系统提示词放在 messages 第一条;响应被正确解析成 `ModelResponse`(工具调用、用量字段)。

`monkeypatch` 是 pytest 提供的"测试期间临时替换/修改"工具,测试结束自动还原。

## `tests/test_agent_loop.py`

`FakeClient.chat` 做了两件事:`copy.deepcopy(kw)` 把每次收到的参数**深拷贝**记录下来(因为 `messages` 列表后续会被继续追加,不拷贝的话回头看到的是被改过的),然后按剧本返回。

| 测试 | 验证 |
|---|---|
| `test_tool_then_done` | 调一次工具再完成:状态 `done`、2 步;第二次请求的最后一条是 `role=tool`,倒数第二条带 `tool_calls`;事件顺序为 `run_start, model_call, tool_result, model_call, run_end` |
| `test_max_steps` | 模型一直调工具,在第 3 步停下,状态 `max_steps` |
| `test_denied_and_unknown_tool` | 用户拒绝的工具与不存在的工具,都得到错误结果,日志里 `is_error` 为真 |
| `test_dangerous_command_blocked_even_when_approved` | 即使用户同意,`sudo rm -rf /` 仍被安全策略拦下 |
| `test_invalid_json_arguments_reported_to_model` | 模型给了非法 JSON 参数,会收到"not valid JSON"错误,运行不崩溃 |
| `test_compaction_elides_then_summarises` | 构造长对话和超大 token 用量,验证先 `elide` 再 `summary` 压缩;压缩后消息角色仍然交替、摘要出现在第一条 |
| `test_summary_sees_unelided_tool_output` | **回归测试**:摘要提示词里必须包含被"抹掉"前的原始工具输出和原始任务,防止"先抹后总结"导致摘要丢信息 |

## `tests/test_eval.py`

`make_task` 用代码动态生成一道最小的题(`f()` 应该返回 2,但现在返回 1),再用假客户端驱动整个 `run_one`。

| 测试 | 验证 |
|---|---|
| `test_pass` | agent 把 `return 1` 改成 `return 2` → 通过;缓存与非缓存 token 分别统计;`changed_files == ["m.py"]` |
| `test_no_edit_failure` | 什么都没改 → 失败类别 `no_edit` |
| `test_tampering_is_restored_and_flagged` | agent 把测试改成 `assert True` → 判分前被恢复,仍然失败,并标记 `tampered_tests` |
| `test_added_test_file_removed` | agent 新增了一个会失败的测试文件 → 被删除不影响判分,但仍标记篡改 |
| `test_max_steps_class` | 步数用尽 → `max_steps` |
| `test_api_error_class` | 模型调用抛异常 → `api_error` |
| `test_split_frozen_and_hash_guard` | 5 题划分得到 2 个 test(`ceil(0.4×5)`);重复冻结结果不变;改动题目内容后 `apply_split` 抛 `SystemExit` |
| `test_report_and_compare` | 统计:`improved == ["t2"]`;通过率 1/3;成本公式;缺价格时成本为 `None`;报告含 "Per task" |
| `test_hidden_tests_are_grading_only` | 可见测试通过但隐藏测试不通过 → 整体不通过;且隐藏测试的内容不会出现在轨迹日志里(agent 看不到) |

`pytest.approx` 用于浮点数比较(`0.1 + 0.2 == 0.3` 在浮点里不成立,要允许微小误差)。
