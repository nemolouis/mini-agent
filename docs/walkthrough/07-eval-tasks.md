# 07 · `miniagent/eval/tasks.py`:任务与 dev/test 划分

## 背景:评测要解决什么

要比较"改之前"和"改之后"哪个更好,题目必须**固定不变**,而且要避免"在同一批题上反复调参,最后只是过拟合这批题"。办法是:把题分成
- **dev**:开发时随便看、随便调;
- **test**:只在版本定稿后跑一次报告。

划分一旦确定就不能变,题目内容被改动也要能检测出来(用哈希)。这个文件就做这些事。

## 任务目录结构(第 1–10 行文档)

```
tasks/<id>/task.json   {"prompt": "...", "test_cmd": "pytest -q"}
tasks/<id>/repo/       agent 看得到的代码仓库(每次运行复制到临时目录)
tasks/<id>/solution/   参考答案,只用于 verify 验证"题目可解"
tasks/<id>/hidden/     隐藏测试,只在判分时放进去,agent 看不到
tasks/SPLIT.json       记录每道题属于 dev 还是 test,以及内容哈希
```

## 第 11–19 行

- 第 13–17 行导入:`hashlib`(哈希)、`json`、`math`(取整)、`dataclass`、`Path`。
- 第 19 行 `TEST_FRACTION = 0.4`:约 40% 的题划为 test。

## 第 22–42 行:`Task` 数据类

字段:`id`、`prompt`、`test_cmd`、`dir`、`hash`、`split`(默认 `None`,等划分后再填)。

三个 `@property`:装饰后可以像**属性**一样访问(`task.repo`)而不用写括号(`task.repo()`)。它们只是拼路径:`repo/`、`solution/`、`hidden/`。

## 第 45–53 行:`task_hash` —— 给任务内容算指纹

```python
h = hashlib.sha256()
files = [d / "task.json"] + sorted(
    p for sub in ("repo", "hidden") if (d / sub).exists()
    for p in (d / sub).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
```
这是一个带多层 `for`/`if` 的生成器表达式,按读代码的顺序理解:
1. 对 `"repo"`、`"hidden"` 两个子目录依次处理,目录存在才处理;
2. 递归列出其中所有文件(`rglob("*")`);
3. 只要文件,排除 `__pycache__`;
4. `sorted(...)` 保证顺序固定(否则哈希不稳定)。

然后第 50–52 行:对每个文件,先喂入"相对路径",再喂入"文件字节内容"。第 53 行 `hexdigest()[:16]` 取十六进制前 16 位当指纹。
- 文件被改、增、删、改名,指纹都会变。
- 注意**不包含 `solution/`**:参考答案可以改,不影响评测题目本身。

## 第 56–57 行:`_id_digest`

把任务 id 做 SHA-256,取前 8 位十六进制,`int(..., 16)` 转成整数。目的:从任务名得到一个**确定的"伪随机数"**,用于稳定地决定划分,不依赖运行顺序。

## 第 60–66 行:`load_tasks`

- 第 63 行 `sorted(p for p in root.iterdir() if p.is_dir() and (p / "task.json").exists())`:遍历 `tasks/` 下的每个子目录,必须有 `task.json` 才算任务,排序保证顺序稳定。
- 第 64 行:读 `task.json`。
- 第 65 行:创建 `Task`,`meta.get("test_cmd", "pytest -q")` 不填则默认 `pytest -q`;`d.name`(目录名)就是任务 id。

## 第 69–84 行:`freeze_split` —— 冻结划分

1. 第 72 行:`SPLIT.json` 存在就读,否则从空白开始。
2. 第 73 行:找出还没划分的新任务 `new`。
3. 第 74–78 行:**首次冻结**(之前没有任何记录):把所有任务按 `_id_digest` 排序,前 `ceil(n × 0.4)` 个划为 `test`,其余 `dev`。这样小任务集上比例也精确(例如 5 题 → 2 题 test)。
4. 第 79–80 行:**以后新增的题**:逐个用 `digest % 100 < 40` 决定(40% 概率进 test),不会动已有题目。
5. 第 81–82 行:写入 `{"split": ..., "hash": ...}`。
6. 第 83 行:写回文件;`sort_keys=True` 让输出稳定、便于看 diff。

关键性质(测试里有验证):**已划分的条目永远不会被改动**,重复调用是幂等的。

## 第 87–98 行:`apply_split`

给每个任务打上 split 标签,并检查两种异常:
- 任务不在 `SPLIT.json` 里 → `SystemExit`,提示先运行 `split`。
- 哈希与记录不一致(题目被偷偷改了) → `SystemExit`,提示"新建一个 id,别直接改"。

`raise SystemExit("...")` 会让程序打印消息并以失败退出,常用于命令行工具的致命错误。
