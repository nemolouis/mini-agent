# 11 · `miniagent/eval/cli.py` 与 `eval/__main__.py`:评测命令行

## `eval/__main__.py`(4 行)

```python
import sys
from .cli import main
sys.exit(main())
```
让你可以用 `python -m miniagent.eval ...` 运行评测:Python 对一个包使用 `-m` 时,会执行包里的 `__main__.py`。

## `eval/cli.py`

`pyproject.toml` 里 `miniagent-eval = "miniagent.eval.cli:main"` 把它注册成命令 `miniagent-eval`。它有 5 个子命令:`split`、`verify`、`run`、`report`、`compare`。

### 第 18–20 行 `_load_price`
读价格 JSON,取出当前模型的那一项;文件不存在返回 `None`。

### 第 23–27 行 `cmd_split`
冻结 dev/test 划分,并打印数量,如 `{'dev': 9, 'test': 6}`。

### 第 30–47 行 `cmd_verify` —— 验证"题目本身是好的"

一道合格的题必须满足:**原始状态下测试失败**,**放入参考答案后测试通过**(并且要通过两次,排除时灵时不灵的"不稳定测试")。
- 第 34 行:遍历每道题;没有 `solution/` 就跳过。
- 第 37 行:`tempfile.TemporaryDirectory()` 临时目录。
- 第 38 行:复制 repo,放入隐藏测试。
- 第 39 行:跑一次得到 `before`。
- 第 40–42 行:把 `solution/` 里每个文件复制覆盖到工作区。
- 第 43 行 `after = [run_tests(w, t.test_cmd)[0] for _ in range(2)]`:跑两次;`[0]` 取返回元组的第一个(是否通过);`_` 是"不需要用这个变量"的惯用名。
- 第 44–45 行:`ok = (not before) and all(after)`;`bad += not ok`(布尔值可以当 0/1 相加)。
- 第 47 行:有问题题目就返回 1(失败退出码)。

### 第 50–100 行 `cmd_run` —— 核心:批量跑评测

1. **读配置与任务(53–57 行)**:配置 JSON → 字典;`apply_split` 校验并打标签;`--tasks` 可以按 id 或前缀筛选(`t.id.startswith(w)`)。
2. **按划分筛选(58–59 行)**:`--split dev|test|all`。
3. **保护 test 集(60–62 行)**:选中了 test 题但没有 `--final` 就拒绝运行。这是用代码强制"test 只在定稿后跑"的纪律。
4. **创建客户端(66–69 行)**:超时、重试次数也可以在配置里调。
5. **准备输出目录(71–73 行)**:
   - `run_id` 默认是"时间戳-配置名"。
   - `out.mkdir(parents=True, exist_ok=False)`:`exist_ok=False` 意味着目录已存在就报错,**防止覆盖之前的结果**。
   - 写 `meta.json`:记录配置、哈希、日期、任务列表及各任务哈希,事后能还原"当时跑了什么"。
6. **并发运行(79–94 行)**:
   - `jobs = [(t, r) for t in tasks for r in range(a.repeat)]`:任务 × 重复次数。
   - `ThreadPoolExecutor(max_workers=...)`:线程池,同时跑多个任务。模型调用大部分时间在等网络,用线程能显著提速。
   - `with A as ex, B as sink:`:一个 `with` 同时管理两个资源(线程池和结果文件)。
   - `futs = {ex.submit(run_one, ...): (t, r) for t, r in jobs}`:`submit` 提交任务并返回 `Future` 对象;字典记录"哪个 future 对应哪个任务"。
   - `for f in as_completed(futs)`:**谁先完成就先处理谁**,边跑边打印。
   - `f.result()`:取返回值;若运行函数里抛了异常,这里会重新抛出,被 `except Exception` 接住并标记为 `HARNESS ERROR`——这是**评测框架自己的 bug**,不算 agent 失败,所以单独醒目地打印到标准错误。
   - 每条结果立刻 `sink.write(...)` 并 `flush()`:运行中途被打断,已完成的结果也不会丢。
7. **生成报告(95–99 行)**:写 `report.md`、`summary.json`,打印一行摘要。

### 第 103–109 行 `cmd_report`
对已有结果目录重新生成报告(例如补了价格表后)。

### 第 112–120 行 `cmd_compare`
对比两个结果目录:
- 第 114 行 `ma, mb = (json.loads(...) for x in (a.a, a.b))`:生成器表达式解包给两个变量。
- 第 115–116 行:两次的划分不同 → 警告。
- 第 117–119 行:同一道题在两次运行里哈希不同(题目被改过) → 警告,因为那样比较就不公平了。

### 第 123–146 行 `main` —— 命令行解析

- 第 125 行:把当前 Python 所在目录加进 `PATH`,让 agent 的 `bash` 工具和判分都能找到虚拟环境里的 `pytest`。
- 第 128 行 `ap.add_subparsers(dest="cmd", required=True)`:子命令机制(类似 `git commit`、`git push`)。
- 每个子命令:`sub.add_parser(...)` 创建,`add_argument(...)` 加参数,`.set_defaults(fn=某函数)` 把"该执行哪个函数"绑定在解析结果上。
- 第 146 行 `return a.fn(a) or 0`:调用对应函数;若函数返回 `None`(没写 return),`or 0` 把它变成退出码 0。

## 完整使用示例

```bash
miniagent-eval split                                              # 冻结划分
miniagent-eval verify                                             # 检查每题可解
miniagent-eval run --split dev --config configs/baseline.json --repeat 3 --workers 4
miniagent-eval report results/<run-id>
miniagent-eval compare results/<run-a> results/<run-b>
```
