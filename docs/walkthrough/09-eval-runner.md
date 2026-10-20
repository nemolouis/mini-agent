# 09 · `miniagent/eval/runner.py`:跑一次评测

**作用**:对一个 `(任务, 配置, 第几次重复)` 完整执行:复制仓库 → 跑 agent → 恢复测试 → 判分 → 汇总成一条记录。

## 第 1–14 行:导入

`from ..agent import ...` 里的 **`..`** 表示"上一级包":当前文件在 `miniagent/eval/`,`..` 就是 `miniagent/`。`from .grade import ...` 的 `.` 则是同级的 `miniagent/eval/grade.py`。

## 第 17–18 行:`config_hash`

```python
hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:10]
```
给配置字典算一个短指纹:`sort_keys=True` 保证键的顺序不影响结果,`.encode()` 把字符串转字节(哈希函数需要字节),取前 10 位。用途:确认两次实验确实用了相同配置。

## 第 21–61 行:`run_one`

函数签名:`run_one(task, cfg, repeat, out_dir, client, keep_workspace=False) -> dict`

**第 22–26 行 准备**
- `run_id = f"{task.id}__r{repeat}"`:如 `01-moving-average__r0`。
- `traj_dir`:这次运行的轨迹目录。
- 系统提示词:默认用 `SYSTEM_PROMPT`;配置里指定了 `system_prompt_file` 就从文件读取(用来做"改提示词"的对比实验)。

**第 28–49 行 在临时目录里跑**
- 第 28 行 `with tempfile.TemporaryDirectory(prefix=...) as tmp:`:创建临时目录,块结束**自动删除**。每次运行都在隔离的拷贝里,绝不污染原任务。
- 第 29–30 行:把任务的 `repo/` 复制到 `tmp/repo`。
- 第 31–39 行:构造 `Agent`。所有可调项都来自配置字典 `cfg`:
  - `cfg["model"]` 必填(用方括号,缺了就报错);
  - 其余用 `cfg.get("max_steps", 30)` 的形式带默认值;
  - `meta` 里记录任务 id、划分、任务哈希、重复序号、配置名与配置哈希,最终写进轨迹的 `run_start`。
  - 没有传 `confirm`,所以用默认的"全部同意"——评测时不能有人工确认,不过黑名单仍然生效。
- 第 40–42 行:计时并运行 agent。
- 第 44 行 `g = restore_tests(task.repo, work)`:**把测试恢复为原始状态**,拿到 `tampered` 与 `changed_files`。
- 第 45 行:放入隐藏测试。
- 第 46 行:跑测试命令,得到 `(passed, test_output)`。
- 第 47–49 行:需要时把最终工作区复制出来留作检查。`import shutil` 写在函数里,是因为只有这条分支才用到。

**第 51 行 读回轨迹**
`[json.loads(l) for l in ...read_text().splitlines()]`:把刚才写的 JSONL 读成事件列表。这一步放在 `with` **之外**(临时目录已经删除),因为轨迹存在 `out_dir`,不在临时目录里。

**第 52–61 行 汇总成一条记录**
```python
rec = {
  "task_id": ..., "passed": passed, "failure_class": classify(...), ...
  **trajectory_stats(events),
}
```
- `final_text[:2000]`、`test_output[-1500:]`:截断,避免记录过大;通过时 `test_output_tail` 为空串。
- `**trajectory_stats(events)`:把统计字段(步数、token、延迟…)平铺合并进同一个字典。

返回的 `rec` 就是 `runs.jsonl` 里的一行,后面 `report.py` 全部基于这些记录做统计。
