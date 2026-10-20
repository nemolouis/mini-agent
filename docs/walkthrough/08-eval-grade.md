# 08 · `miniagent/eval/grade.py`:判分、防作弊、失败归因

## 要防的"作弊"

agent 的目标是"让测试通过"。最省事的办法是**直接改测试**(比如把断言改成 `assert True`)。所以判分时不能信任 agent 动过的工作区,要:
1. 把测试文件**从原始副本覆盖回去**;
2. 把"动过测试"**记录成一个标记**;
3. 参考答案、隐藏测试在 agent 看不到的地方。

## 第 1–14 行

导入 `os`、`shutil`(复制/删除目录)、`subprocess`、`sys`、`Path`。`GRADE_TIMEOUT = 120`:判分命令最多跑 120 秒。

## 第 17–19 行:`is_test_file(rel)`

判断一个相对路径是不是测试文件:文件名以 `test_` 开头,或以 `_test.py` 结尾,或路径中含 `tests` / `test` 目录。`rel.name` 是文件名,`rel.parts` 是路径的各段。

## 第 22–24 行:`_files(root)`

返回 `{相对路径: 文件字节}` 的字典(字典推导),排除 `__pycache__` 与 `.pytest_cache`。用于比较"原始"和"agent 改完后"的两个目录。

## 第 27–46 行:`restore_tests`

```python
orig, now = _files(pristine), _files(work)
```
`orig` = 原始仓库内容,`now` = agent 改完后的工作区内容。

1. 遍历原始的每个文件(32–39 行):
   - **是测试文件**且内容变了(或被删了:`now.get(rel)` 取不到得 `None`,与原内容不相等)→ 标记 `tampered=True`,并把原始内容写回。
   - **不是测试文件**且内容变了 → 记入 `changed`(这就是 agent 真正的修改)。
2. 遍历 agent 新增的文件(40–45 行):`now.keys() - orig.keys()` 是字典键的**集合差**。
   - 新增了测试文件 → 标记 `tampered`,并 `unlink()` 删掉(`unlink` = 删除文件)。
   - 新增了普通文件 → 记入 `changed`。
3. 返回 `{"tampered": bool, "changed_files": 排序后的列表}`。

## 第 49–57 行:`run_tests`

```python
env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{...}", "PYTHONDONTWRITEBYTECODE": "1"}
```
- 把当前 Python 解释器所在目录(虚拟环境的 `bin`)放到 `PATH` 最前面,保证命令里的 `pytest` 找到的是项目环境里的。
- `os.pathsep` 是路径分隔符(Unix `:`,Windows `;`)。
- `PYTHONDONTWRITEBYTECODE=1` 不生成 `.pyc`,避免污染工作区。

执行:`subprocess.run(["bash", "-c", test_cmd], cwd=work, ..., timeout=timeout)`。
- 超时 → 返回 `(False, "grading timed out ...")`。
- 否则 `returncode == 0` 表示测试通过;输出取最后 3000 字符。
- 返回类型 `tuple[bool, str]`:一次返回两个值,调用方用 `passed, output = run_tests(...)` 解包。

## 第 60–63 行:`add_hidden`

如果有 `hidden/` 目录,就把里面的文件复制进工作区(`dirs_exist_ok=True` 允许合并进已存在的目录)。**在 agent 跑完之后才放进去**,所以 agent 永远看不到隐藏测试,也无法针对它"凑答案"。

## 第 66–67 行:`copy_repo`

把任务的 `repo/` 复制到工作区,忽略 `__pycache__` 和 `.pytest_cache`。

## 第 70–88 行:`classify` —— 失败归因

给每次失败的运行一个**互斥的一级类别**,按固定优先级依次判断(靠前的先命中就返回):

| 顺序 | 条件 | 类别 |
|---|---|---|
| 0 | 通过了 | `pass` |
| 1 | `run_end` 状态是 error 或根本没有 `run_end` | `api_error` |
| 2 | 步数用尽 | `max_steps` |
| 3 | 回复被 `max_tokens` 截断 | `max_tokens` |
| 4 | 其它非正常状态(如内容过滤) | `stopped_<状态>` |
| 5 | 动过测试 | `tampered_tests` |
| 6 | 没有改任何非测试文件 | `no_edit` |
| 7 | 改了但测试仍不过 | `tests_failed_after_edit` |

第 74 行 `next((e for e in reversed(events) if e["event"] == "run_end"), None)`:
- `reversed(events)` 倒序遍历事件;
- 生成器里找第一个 `run_end`;
- `next(迭代器, 默认值)` 取第一个,找不到返回 `None`。

互斥且有顺序,意味着统计时每次失败只被算入一个桶,便于画分布。

## 第 91–108 行:`trajectory_stats` —— 从日志算指标

- 第 92–93 行:分别取出所有 `model_call` 和 `tool_result` 事件。
- 第 94 行 `u = lambda k: sum(c["usage"].get(k, 0) or 0 for c in calls)`:定义一个小函数,"把所有模型调用的某项用量求和"。
- 第 95 行:`total_in` 是总输入 token(已包含缓存命中的部分),`cached` 是缓存命中的部分,所以**未缓存输入 = total_in - cached**(第 99 行)。
- 返回的字段:
  - `response_models`:服务器报告用过的模型名集合(集合推导 `{...} - {""}` 去掉空串)。
  - `steps`:模型调用次数。
  - `uncached_input_tokens` / `cache_read_tokens` / `cache_creation_tokens`(恒为 0,DeepSeek 不单独报告)/ `output_tokens`:分开是因为它们**价格不同**,算成本要分别乘价格。
  - `model_latency_s`:所有模型调用耗时之和。
  - `tool_calls`、`tool_errors`:工具次数和出错次数。
  - `blocked_commands`:被安全策略拦截的次数(输出里含 `blocked by safety policy`)。
  - `compactions`:发生"摘要式压缩"的次数。
- `sum(1 for t in tools if cond)`:数满足条件的元素个数的惯用法。
