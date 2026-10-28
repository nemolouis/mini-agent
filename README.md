# mini-agent

一个从零手写的最小 coding agent，附带评测 harness。不依赖 LangChain 等 agent 框架，目标是**用数据说明 agent 好不好，以及每次改动带来了多少变化**。

> 状态：M1–M4（agent、评测、回放、MCP）已完成；M5（可验证任务生成 → 轨迹合成 → SFT → 评测）**闭环跑通了一圈，效果很小且统计上不显著**：任务、沙箱、轨迹合成、导出、LoRA 训练（第三次成功，前两次发散）、训练前后评测都做了。在 dev 的 48 题（两个未见过的库）上，学生模型从 **0/48 到 4/48**（Fisher/McNemar p≈0.12，**不显著**）；明确的是行为变化：训练前一次工具调用都没有，训练后 48 次都在用工具、8 次改了文件。数据消融和 test 集没做。**之后又做了三轮改进（edit_file 提示、缩短 old_string、普通文本工具调用格式），都没有提高通过数；最有价值的发现是 `<tool_call>` 标记 token 未训练导致工具调用不稳定，4/48 不应当作稳定能力引用，下层部分到此收工（理由见 [docs/next_phase_plan.md](docs/next_phase_plan.md) 末尾）。** 下面所有数字都来自真实运行，样本小的地方标了区间；两个 test 集（手写题 17 题、生成题 47 题）**都还没有跑过**。范围与验收标准见 [PROJECT.md](PROJECT.md)，M5 的计划与逐步记录见 [docs/next_phase_plan.md](docs/next_phase_plan.md)。

**这个项目是什么**：一个标准库实现的 coding agent（`miniagent/` 约 4.1k 行，无 agent 框架、无第三方 SDK；只有训练脚本 `scripts/sft_mlx.py` 用到 MLX，装在单独的环境里），加上能回答"改动到底有没有用"的评测与回放工具，以及一个按"参数是攻击者输入"设计的 MCP 服务器。它的价值不在于分数，而在于**每个结论都有运行记录、预测先写后跑、预测错了也记下来**：15 条失败案例里有 loop 自己的 bug、harness 的 bug、我出的题的 bug，也有模型的行为问题。

```
任务（repo + 隐藏测试） ─▶ agent 循环 ─▶ 轨迹 JSONL ─▶ 规则化判分 / 失败归因 ─▶ 报告、配对对比
                           │   ▲                          │
                           ▼   │                          ▼
                     内置工具 / MCP 工具             回放网页（单次 / A-B 并排）
```

## 当前进度

| 部分 | 状态 | 说明 |
|---|---|---|
| M1 agent 主循环与工具 | 完成 | 见"特性"；全仓库 373 个测试（不调用模型；需要 Docker 的测试在没有 Docker 时自动跳过） |
| M2 评测 harness | 完成 | 任务集、dev/test 划分、隐藏测试、规则化判分、配对对比、断点续跑；实验结果见"结果"；test 集未跑 |
| M3 轨迹回放 | 完成 | `miniagent-eval view`：浏览所有运行、逐步回放、两次运行并排对比；未做按条件导出轨迹 |
| M4 MCP server | 完成 | 手写的 MCP 笔记服务器 + 客户端 + 越界/越权测试（见"MCP 服务器"）；未用官方客户端做互操作验证 |
| M5-a 回放、沙箱、任务生成 | 完成 | 确定性回放；Docker 沙箱（有逃逸测试）；变异式任务生成，352 题全部在沙箱里通过 verify |
| M5-b teacher 轨迹合成与导出 | 完成 | DeepSeek flash 在 257 道 train 题上 2 次采样，513/514 通过，导出 510 条训练样本 |
| M5-c LoRA 训练 | 完成（第 3 次） | 本机 MLX、4 位基础权重、只对助手轮算 loss、只训练最后 16 层。前两次发散（原因线索见 docs/next_phase_plan.md）；第三次 456 步没有发散，验证损失 2.10 → 0.74 |
| M5-d 训练后评测与消融 | 评测做了，消融和 test 没做 | dev：基础 0/48，训练后 4/48（p≈0.12，不显著）。34 个 `no_edit` 里 `edit_file` 29/31 次报错、20 个仍声称已修好。后续三轮改进实验（edit_file 提示、缩短 old_string、普通文本工具调用格式）都没有提高通过数，见"后续实验" |

## 主要发现

1. **评测集对强模型会饱和，难度是相对于模型的。** DeepSeek flash 在 B 层 13 道 dev 题上 90%；同一批题上 Gemini 3.5-flash-lite 约 54%、3.1-flash-lite 约 26%。与其不断出更难的题，不如用**一组强弱不同的模型**当阶梯（[失败案例 11](docs/failure_cases.md)）。
2. **失败的大头是"假完成"**：Gemini 3.1-flash-lite 的 29 次失败里有 21 次（72%）是模型自己最后一次跑测试全绿后宣布完成，而失败的隐藏测试覆盖的是文档里写明、可见测试没覆盖的规则（[案例 13](docs/failure_cases.md)）。这是单个模型的观察，不是对所有 LLM 的结论。
3. **第一轮 87% 里有 4 次"失败"其实是我出的题有缺陷**（spec 与隐藏测试矛盾或遗漏），真实通过率约 97%。隐藏测试里的每个断言必须能从可见规格推出（[案例 10](docs/failure_cases.md)）。
4. **上下文压缩有两个真实缺陷**：先抹掉输出再做摘要导致摘要丢信息（已修）；压缩后仍超阈值导致**每一步都压缩**、把步数预算耗尽（已修：模拟里 25 步 22 次摘要 → 3 次；Gemini 3.5 真实重跑每次运行 ≤6 次摘要、平均 29.5 步，修复前约 31 次、42 步；一条预测没中，见 [案例 1、2](docs/failure_cases.md)）。
5. **小样本下无法检出小效应**：在弱模型上，"要求做规格验证的提示词"和"开启思考"都只多过 1 题（13 题 × 1 次），无法与噪声区分；去掉 `bash`（不能跑测试）也没有让 DeepSeek 变差（[消融](docs/ablations.md)）。

## 特性（已实现）

- **agent 主循环**：直接调用模型的 function calling 接口，最大步数限制，可配置模型、temperature、系统提示词、可用工具
- **工具**：`read_file` / `write_file` / `edit_file`（要求匹配唯一）/ `bash`（超时、输出截断，超时会杀掉整个进程组）/ `grep`；文件路径限制在工作区内
- **权限与安全**：写文件和 shell 需确认；危险命令硬拦截（`--yes` 也无法绕过）
- **上下文管理**：先抹掉旧的工具输出，仍超限再让模型做摘要；保证 tool_calls 与对应 tool 消息成对、不被切断；压缩后仍超阈值时不再逐步重试，而是等输入增长 `compact_regrowth`（默认翻倍）后再压（案例 2）
- **轨迹落盘**：每次运行写一份 JSONL，包含模型输出、工具调用与结果、耗时、token（含缓存与推理 token）、压缩事件、服务端自报的模型名
- **录制与回放**（`miniagent/replay.py`、`miniagent-eval replay`）：`CassetteClient` 按请求哈希缓存模型响应（`run --cassette 文件 --cassette-mode auto|record|replay`，replay 模式不需要 API key，没录过的请求直接报错而不是联网）；`replay` 命令把旧轨迹里的模型回答按顺序喂给**当前**的主循环，在新的任务副本里真实执行工具，逐步比对工具调用、压缩时机和结束状态，用来零成本检查"改了 loop 之后行为变没变"。局限：回放不能预测新模型或新提示词的行为；压缩决策依赖按字符数估算的历史长度，所以工作区路径长度、Gemini 思考签名这类细节都会影响结果（旧的 Gemini 轨迹没记签名，回放时会跳过并说明原因）。
- **SFT 数据导出**（`miniagent-eval export`）：把通过的运行写成聊天格式 JSONL（system、tools、带 tool_calls 的 assistant、tool 消息）。只留隐藏测试通过且自己结束、没改测试、没发生压缩、没有非法工具参数的运行；默认只导出 `train` 划分（`--splits` 可改；dev、test 和没有划分的手写题都不会进训练数据）；精确重复去重；每种跳过原因都计数。`run_start` 现在记录系统提示词全文和工具定义；`log_reasoning: true` 时记录模型的可见思考。
- **Docker 沙箱**（`miniagent/sandbox.py`，设计见 [docs/m5_sandbox_taskgen_design.md](docs/m5_sandbox_taskgen_design.md)）：`miniagent --sandbox`、`miniagent-eval run --sandbox`（或配置里 `"sandbox": true`）让 `bash` 和判分用的测试都跑在容器里：断网、根文件系统只读、去掉全部 capability、非 root、不传任何环境变量（拿不到 API key）、限制进程数/内存/CPU，只挂载工作区。每个运行一个长驻容器、每条命令一次 `docker exec`；命令超时或容器出问题时换新容器；输出有上限，洪水不会撑爆宿主内存。镜像用 `miniagent-eval sandbox-build` 构建，`sandbox-clean` 清理崩溃遗留的容器。沙箱自身故障（Docker 挂了等）让运行以 error 结束、不计入通过率，不会当作工具结果显示给模型。21 个测试（其中 18 个对真实容器做逃逸检查），对每个安全选项做过变异检验。**不是虚拟机**：容器与宿主共享内核。
- **变异式任务生成**（`miniagent-eval gen`，`miniagent/taskgen/`）：对"能通过自带测试的种子库"注入一个小 bug（比较/算术/布尔运算符、条件取反、整数常量±1、break↔continue、删除语句），只在能通过全部筛选时才保留为任务：能编译、原代码通过全部测试、可见测试至少失败一个、失败数不多、两次结果一致且不超时、同一失败模式的任务有数量上限、构造出的任务本身再核对一遍。可见测试是种子测试的随机子集，隐藏测试是完整文件。不调用任何模型。生成的任务放在 `gen_tasks/`（不进入 `tasks/` 与既有的 dev/test 划分），**按种子库划分** train/dev/test，导出 SFT 数据默认只取 train。
- **模型接入**：标准库实现，无第三方 SDK。两种协议：OpenAI 兼容的 chat completions（DeepSeek、智谱 GLM 已验证）和 **Gemini 原生 `generateContent`**（含思考签名的保存与回放，可经转发型中转使用）。配置文件里用 `base_url` / `base_url_env` / `api_key_env` / `extra_body` / `api_style` 指定，密钥永远从环境变量读

**尚未实现**（避免误解）：参数 JSON schema 校验、并行工具调用、按条件导出轨迹到网页之外的格式（SFT 导出已有，见上）、HTTP 传输的 MCP。

## 快速开始

```bash
git clone <this-repo> && cd mini-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q                          # 单元测试，不调用模型

# 密钥通过环境变量传入，不要写进仓库。配置里的 api_key_env 指明用哪个变量，例如：
export DEEPSEEK_API_KEY="..."      # configs/flash.json
export GEMINI_API_KEY="..."        # 直连 Google 的配置
export RELAY_BASE_URL="https://你自己部署的中转"; export RELAY_API_KEY="..."   # configs/g35-lite-relay.json 等

scripts/run_task.sh 01 -y          # 在一个任务上运行 agent 并判分
```

对任意仓库直接使用：

```bash
miniagent "修复 stats.py 里 moving_average 的 bug" -w path/to/repo -m <model>
```

常用参数：`--max-steps`、`-y`（自动批准写/改/命令，黑名单仍生效）、`--context-limit`（调低可触发压缩）、`--keep-recent`。

## 评测（M2）

```bash
miniagent-eval run --config configs/flash.json --split dev --tasks b --repeat 3 --workers 4
miniagent-eval report results/<run-id>
miniagent-eval compare results/<run-a> results/<run-b>
miniagent-eval verify              # 每题：初始必须失败、参考解必须通过
```

- **任务**：`tasks/<id>/{task.json, repo/, hidden/, solution/}`。`solution/` 只用于验证题目可解，`hidden/` 是只在判分时放入的隐藏测试，agent 都看不到。A 层（`01`～`15`）是自建小题，B 层（`b01`～`b26`）是 2～5 文件的规格驱动题，关键行为写在 `docs/` 或 docstring 里。第二批 B 题的隐藏测试多用暴力解、Python 标准库或数学性质做独立判分器。共 41 个目录，2 个已退役（见案例 10），在用 39 个。
- **划分**：`tasks/SPLIT.json` 固定 dev / test（在用任务：dev 22 = A 9 + B 13，test 17 = A 6 + B 11），并保存每题内容哈希，任务被改动会报错；已被运行过的题不原地修改，只能新建 id。
- **判分**：判分前从原始副本覆盖回测试文件、删除 agent 新增的测试文件；改动过测试只作标记，不作失败类别。
- **指标**：通过率（按题平均，bootstrap 区间）、步数、token、成本（价格表 `configs/prices.json`，分高峰/低谷两档）、延迟、失败归因；`compare` 做同题配对并列出翻转的题。
- **失败归因**：规则化、互斥：`api_error`（**不计入通过率**，报告会标出排除了几次）/ `max_steps` / `max_tokens` / `no_edit` / `tests_failed_after_edit`。另有非互斥标记：是否改过测试、压缩次数、工具报错、"假完成"（失败但自己最后一次测试是绿的）。
- **免费档/限额场景**：`--resume <results目录>` 只补跑没有有效结果的运行（加 `--repeat N` 可扩展重复次数）；`--max-requests N` 用完请求预算就停；`--subset <名>` 使用 `tasks/SUBSETS.json` 里的命名子集；遇到永久性错误（模型不可用、余额不足、日额度耗尽）立即停止整批。

## 回放与对比（M3）

```bash
miniagent-eval view results/<run-id> [results/<other-run-id> ...] [runs]
```

在本机起一个只读网页（默认 `http://127.0.0.1:8765/`），不需要任何前端依赖：

- **Runs**：列出一个结果目录里的所有运行（任务、重复、通过/失败类别、步数、token、耗时，`flags` 列是压缩次数、"假完成"、重试等标记），可按任务、失败类别、通过与否筛选（输入筛选词时输入框保持焦点）；可以同时挂多个目录，**A 和 B 可以来自不同目录**（例如基线 vs 某个消融）。
  - **选择 A / B**：每行最右的 `pick` 列有 `A`、`B` 两个按钮，点击只记录选择、**不离开 Runs 页**，已选的那一行按钮会高亮。顶部的选择栏显示当前的 A、B（可用 `✕` 清除），两个都选好后点 **Compare A / B** 进入对比，`View A` 进入单次回放。双击某一行则直接把它作为 A 打开并进入回放。
  - 载入失败（轨迹不存在、格式错误）会弹出错误提示，不会静默无反应。
- **Run A**：单次运行逐步回放：每步的模型输出、工具调用与参数、工具结果（可折叠）、耗时、token（含缓存与推理）、压缩事件和摘要内容；顶部有时间线，柱高是模型延迟，`C` 标记该步之前发生了压缩，点击跳转到对应步骤。
- **Compare A / B**：两次运行的汇总对比（步数、token、耗时、压缩次数、工具报错）、并排时间线、按步骤对齐的并排视图，并标出第一次动作分叉的位置。例如把 `ctx3k` 和基线的同一题并排，能直接看到 B 每步前都在压缩（案例 2）。A、B 不是同一道题时顶部会给出警告（逐步对齐与分叉标记此时没有意义）；只选了一个时会明确提示缺的是哪个。B 只出现在对比页，没有单独的 "Run B" 页面，要单独回放请把它载入为 A。
- 也支持直接用浏览器打开 `miniagent/eval/viewer/index.html`，用"Load A / Load B"载入单个 `trajectory.jsonl`（静态模式，没有运行列表）。早期格式的旧轨迹也能打开。
- **安全**：服务只绑定 `127.0.0.1`，拒绝 Host 头不是本机的请求（防 DNS 重绑定），只提供页面和命令行给定目录内的 `trajectory.jsonl`（轨迹 id 严格校验，解析后的路径必须在目录内）；页面把轨迹内容全部当作文本渲染，不会执行其中的 HTML。

## MCP 服务器（M4）

一个手写的、只读为主的 MCP 笔记服务器，加上 agent 侧的 MCP 客户端。设计与取舍见 [docs/m4_design.md](docs/m4_design.md)。

```bash
python3 scripts/mcp_demo.py        # 不需要模型或 API key：演示边界（含笔记里的提示注入、符号链接、FIFO、越权调用）

# 让 agent 通过 MCP 读笔记（把内置的读文件/命令工具隐藏，只剩 MCP 工具）
miniagent "规划会议上定的月度预算是多少？" -w examples -y -m deepseek-flash \
  --mcp-config examples/mcp_notes.json --disable-tools bash,grep,read_file,write_file,edit_file
```

- **服务端**（`miniagent/mcp/notes_server.py`，标准库）：工具 `list_notes` / `read_note` / `search_notes`，以及默认**不存在**的写工具 `append_note`（只有 `--allow-write` 才启用）。同时支持新版协议（2026-07-28，每个请求自带版本和能力元数据，实现了 `server/discover`）和旧版握手（`initialize`）。stdout 只写 JSON-RPC，日志写 stderr，stdin 关闭即退出。
- **路径安全**（`miniagent/mcp/safepath.py`）：工具参数一律当作攻击者输入。目录逐级用文件描述符 `openat` 打开且带 `O_NOFOLLOW`（检查和打开是同一个原子操作，没有"检查后被替换"的窗口，任何一级是符号链接就失败）；最终文件必须是单链接的普通文件（拒绝 FIFO、设备、硬链接）；只认 `.md/.txt/.rst`；`.` 开头的任何分量、`..`、绝对路径、`~`、NUL、反斜杠一律拒绝；不做 URL 解码；"不存在"和"不允许"返回同样的话，报错里不出现真实路径；有大小、数量、耗时上限；搜索是字面量，没有 ReDoS。
- **越权**：只读模式下 `append_note` 不在 `tools/list` 里，直接调用也只得到"未知工具"，磁盘上不会出现任何文件；`--allow-tools` 之外的工具同样不存在。agent 侧只暴露配置里 `allow` 列出的工具（名字加前缀 `mcp__notes__`），模型调用没暴露的名字时根本不会联系服务端；MCP 工具默认需要确认（规范说工具注解不可信）。
- **客户端**（`miniagent/mcp/client.py`）：按规范先探测 `server/discover`，失败再回退到旧版握手；请求超时会发取消通知；独立进程组启动、关闭时按"关 stdin → SIGTERM → SIGKILL"收尾；stderr 单独读取，不会因日志太多而死锁；服务端只拿到最小环境变量，**拿不到我们的 API key**。
- **测试**（166 个，`tests/test_mcp_*.py`）：协议两代、各错误码和畸形输入；路径攻击（数十种写法，用真实的符号链接、硬链接、FIFO）；用钩子在"检查"和"打开"之间换文件的 TOCTOU；越权调用；客户端对 8 种行为异常的假服务端（旧版、静默、版本不匹配、超时、stderr 洪水、崩溃、拒绝退出、分页）；agent 集成，包括"被笔记诱导的模型"。我还做了**变异检验**：逐个去掉防御共 18 次，15 次让测试失败，3 次存活（都是因为有冗余防线，详见设计文档）。

不是沙箱：服务端以你的用户身份运行，上面都是应用层的检查，一个绕过检查的漏洞仍可读到你能读的文件；根目录应使用专用目录；硬链接检测靠 `st_nlink`（会误伤极少数合法情况）；提示注入没有被"解决"，只是让服务端的边界不依赖模型的判断。

## M5：从可验证任务到 SFT（做到一半）

目标是补上"下层"的一条完整链路：**可验证任务 → teacher 轨迹 → SFT → 用同一套 harness 评测前后差异**。逐步记录、每个决定的理由和被推翻的假设见 [docs/next_phase_plan.md](docs/next_phase_plan.md)，沙箱与生成器的设计见 [docs/m5_sandbox_taskgen_design.md](docs/m5_sandbox_taskgen_design.md)。

```
种子库(seeds/) ─▶ 变异+筛选 ─▶ 352 道题(按种子库分 train/dev/test) ─▶ teacher 采样 ─▶ 导出(只取 train) ─▶ LoRA ─▶ 评测(dev/test: 未见过的库)
                  (沙箱内)       每道题都过 verify                     (DeepSeek flash)    510 条            (第3次成功)  (dev 0→4/48)
```

```bash
miniagent-eval sandbox-build                                              # 沙箱镜像(需要 Docker)
miniagent-eval gen --seeds seeds --out gen_tasks --per-seed 24            # 生成任务
miniagent-eval --tasks-root gen_tasks verify --sandbox --workers 4        # 每题:初始必须失败、参考解必须通过
miniagent-eval --tasks-root gen_tasks run --config configs/gen-synth-flash.json --split train --sandbox --workers 4 --repeat 2
miniagent-eval export results/<run-dir> --out data/sft_train_v2.jsonl --models deepseek-flash
# 训练在单独的环境里(Python venv + mlx-lm),脚本见 scripts/sft_mlx.py:
python3 -m venv .venv-mlx && .venv-mlx/bin/pip install --only-binary :all: mlx-lm
.venv-mlx/bin/python scripts/sft_mlx.py check --model models/<m> --data data/sft_train_v2.jsonl     # 验证 token 数与助手轮掩码
.venv-mlx/bin/python scripts/sft_mlx.py train --model models/<m> --data data/sft_train_v2.jsonl --out adapters/<name> --max-len 8192 --epochs 2 --accum 4
```

已经测到的事实(全部带样本量):

- **题目**:352 道,来自 16 个种子库(14 个 PyPI 小库 + 2 个手写)。对种子库注入一个小 bug,只有同时满足下列条件才保留:能编译、原代码通过全部测试、可见测试至少失败一个、失败数不多、两次结果一致且不超时、同一失败模式只留少数、构造出的任务本身再核对一遍。划分**按种子库**:train 257 题(12 个库)、dev 48 题(colorama、schema)、test 47 题(sqlparse、xmltodict)。
- **teacher**:30 道题的试点上,DeepSeek flash 30/30、平均 8.3 步,Gemini 3.5-flash-lite 25/30、15.0 步(配对差 +16.7 点,区间 3.3~30.0,样本小)。放量用 DeepSeek:257 题 × 2 次,513/514 通过;价格表估算每次约 $0.002~0.004(价格表里的列对应关系标注了"待核对",以账户余额为准)。
- **训练数据**:510 条,覆盖 257 题、12 个库;真实 token 数共 371 万,中位 6.2k,p90 13.1k,最大 32k;只有 9.1% 的 token 有 loss(助手轮)。≤8192 token 的有 330 条(65%)。训练 `--max-len 8192`,更长的**整条丢弃、不截断**,所以实际训练集 313 条,**偏向短而简单的题**。
- **训练前基线**:未训练的 Qwen2.5-Coder-1.5B-Instruct 在 dev 48 题上 **0/48**,48 次都是 `no_edit`、1 步:它不按 `<tool_call>` 格式调用工具(输出 JSON 代码块或计划文字),服务端因此没有解析出工具调用。这个 0% 说的是"格式不会",不是"修不好 bug"。训练后如果有提升,要把"学会了格式"和"真的会修"分开看(失败类别、修改的文件),不能只报一个通过率。
- **沙箱**:见"特性"。验证 352 道题时发现过一个间歇性问题:新容器偶尔读到宿主刚替换过的文件的旧版本(判分时约 8/100),已用"判分用新副本 + 每条命令前对齐文件清单,对不上就报错"修复(0/300)。

**训练与评测的实际情况**（完整记录、数字和局限见 [docs/next_phase_plan.md](docs/next_phase_plan.md)）：

- **训练**：前两次发散（第一次学习率 1e-4、无监控，白跑 5.5 小时；第二次被自动止损守卫在第 88 步停下）。第三次打开了 Adam 偏差修正（MLX 的 AdamW 默认关闭，会把前 100 次更新的步长放大 3~6 倍，已用数值验证），并只训练最后 16 层（第 0 层的 LoRA 梯度比其他层大约 14 个数量级），456 步没有发散。这和"偏差修正是原因"一致，但只有一次运行、同时改了几样，**因果是推断，不是证明**。调试显存时还触发过一次 macOS 内核崩溃。
- **一个有意思的根因**：Qwen2.5-Coder-1.5B 的 `<tool_call>`/`</tool_call>` 两个 token 的嵌入是没训练过的占位值（与 124 号 token 相差约一个 bf16 舍入单位），输出层与嵌入共享权重，所以微调后的模型学会了整个格式，却只能在标记位置输出 124，服务端收不到工具调用。客户端因此提供 `text_tool_calls`（宽容地读回复里的 JSON 工具调用，默认关闭，有测试）；训练前基线用同样的解析重测。
- **结果**：dev 48 题，基础 0/48，训练后 4/48（95% 区间 3.3%~19.6%，Fisher p=0.117，**不显著**）。训练前一次工具调用都没有，训练后 48 次都有、8 次改了文件。失败主要是 `edit_file` 抄不准要替换的代码（31 次编辑 29 次报错）、以及编辑失败后仍声称已修好（20 个）。验证损失最低的第 300 步检查点端到端是 0/48，说明用 7 条验证样本的损失挑检查点不可靠。

**还没做**：数据消融（带/不带思考文本、数据量、是否过滤）、一次 test 集评测、只改 Adam 偏差修正的对照实验、每题多次重复以缩小区间、按步切窗的训练（只做了统计）。

### 后续实验（2026-10-25～26）：都没有带来通过数提升

训练后想改进 `edit_file` 失败的问题，做了三轮，**结果都是负面或无效**，完整记录在 `docs/next_phase_plan.md`。以下都是 dev 48 题、每题 1 次、温度 0，与上面 4/48 的基线逐题配对。

- **给 `edit_file` 的失败信息加提示**（返回文件里最相近的真实行和行号，`edit_hints`，默认关）：4/48 → 3/48，退步 1 题、改进 0 题，没有帮助。原因：失败之后模型下一次调用与上一次完全相同的有 51/58；94 次编辑里 76 次的 `old_string` 在之前的任何工具输出里都找不到，是凭空写的。训练数据里 95% 的首次编辑是照着读到的内容抄的，但没有任何"失败后纠正"的样本（老师的 513 次编辑调用也是 0 次失败）。
- **把 `old_string` 缩短后重训（v4）**：0/48，48 次运行都是说一句话就结束、没有发出工具调用，所以这一轮**不能说明缩短有用或没用**。
- **根因是工具调用标记 token**：`<tool_call>` 的嵌入没训练过，模型能否发出标记取决于权重里很小的差异，不同检查点会随机翻转。因此上面基线的 4/48 依赖一个不稳定的状态，**不应当作稳定能力引用**。
- **改成普通文本工具调用格式（`[TOOL_CALL]`，v5）**：格式层的问题解决了——48/48 次运行都发出了工具调用（共 623 次，基线 333 次）；但通过 0/48，`edit_file` 全程只用了 1 次，54% 的调用与上一次完全相同（反复跑同一条 pytest）。也就是说下一层问题是行为：学生不会从探索转到修改。基线 4/48 对 0/48 的差异（McNemar 精确检验 p=0.125）不显著，也不能由此推出新格式更差——两次训练的数据条数不同（152 对 144），也没有重复运行。
- **数据量的瓶颈**：510 条里只有约 144～160 条放得下 4096 token（本机 16 GB 内存的限制）。把过长的工具输出截断只多留约 17% 的可用样本，而且会让 `old_string` 在前文不可见，不值得做；按步切窗能得到约 244 条可用的编辑样本（约 +74%），但总 token 量约是现在的 14 倍，本机跑不动，没有做。

## 结果

### 模型阶梯（B 层 dev，13 题）

同一套任务、同一个 harness，换模型。通过率为按题平均，括号是 95% 区间。

| 模型（配置） | 日期 | 重复 | 有效运行 | 通过率 | 平均步数 | 平均成本/次 |
|---|---|---|---|---|---|---|
| deepseek-flash（`flash`） | 10-13 | 3 | 39 | **89.7%**（77–100） | 8.7 | $0.0056（低谷价）/ $0.0113（高峰价） |
| gemini-3.5-flash-lite（`g35-lite-relay`） | 10-16 | 1 | 13 | **53.8%**（31–77） | 22.2 | 免费档 |
| gemini-3.1-flash-lite（`gemini-relay-native`） | 10-15 | 3 | 39 | **25.6%**（8–44） | 24.1 | 免费档 |
| glm-4.7-flash（免费档，`glm-flash`） | 10-12 | – | 11（另有 6 次 API 失败） | 0 / 11 | – | 免费档 |

说明：GLM 那一轮在 17 次运行、4.9 小时后被中断（限流 + 思考失控），只供参考；3.5-flash-lite 另有一轮较早的直连数据（23 次有效运行，8 题约 73%），因额度耗尽未跑完，未列入。DeepSeek pro 只在更早的 6 题集合上跑过（88.9%，成本约为 flash 的 8 倍），不在同一集合，未列入。

### 有信息量子集上的新基线（Gemini 3.5-flash-lite，`g35-mid`，4 题 × 3 次）

子集是用 3.5-flash-lite 早先的运行挑出来的（通过率在 0.25–0.75 之间的题），然后**重新跑**一次基线：

| 题 | 选题时的通过率（早期合并运行） | 新基线（3 次） |
|---|---|---|
| b08-csv-loader | 0.75（n=4） | 0.67 |
| b12-sessions | 0.50（n=4） | 0.33 |
| b13-interval-set | 0.50（n=4） | 0.00 |
| b16-text-diff | 0.67（n=3） | 0.33 |
| **平均** | **0.60** | **0.33**（4/12，区间 8–58；平均 22.6 步，271 次请求） |

选题时平均 60%，新基线只有 33%：这就是"用同一批运行挑题，估计值会被拉向中间"的回归均值效应，也是 `tasks/SUBSETS.json` 要求对照条件必须与**新跑的基线**比、不能与选题用的旧数据比的原因。压缩修复的两组实验就在这个子集上跑（下一节）；其他对照条件（no-bash 等）**没有运行**。

### 消融（DeepSeek flash，13 题 × 3 次，基线 90%）

每个条件只改一处；预测在运行前写进了配置的 `hypothesis`。详见 [docs/ablations.md](docs/ablations.md)。

| 条件 | 通过率 | 平均步数 | 预测 | 判定 |
|---|---|---|---|---|
| no-bash（不能跑测试） | 97% | 8.6 | 掉 10–25 点 | **被推翻** |
| steps10（步数上限 10） | 95% | 8.2 | 掉 15–30 点 | **被推翻**（我的预测基于过时的步数分布） |
| ctx3k（压缩阈值 3000） | 77% | **41.8** | 掉 10–30 点，因摘要丢信息 | 方向对，**机制错**：是每步压缩导致步数耗尽（缺陷已修，见下一节） |
| no-grep、no-verify-prompt | – | – | – | **未评估**：账户余额用完（HTTP 402） |

### 压缩修复的真实验证（Gemini 3.5-flash-lite，`g35-mid`）

预测写在 `configs/g35-ctx3k-fixed.json` 和 `configs/g35-ctx12k.json`，运行后逐条核对（[案例 2](docs/failure_cases.md)）。

| 条件 | 运行数 | 每次运行的摘要压缩次数 | 平均步数 | 通过 | 预测 |
|---|---|---|---|---|---|
| 修复前（DeepSeek，ctx3k） | 39 | 约 31 | 41.8 | 77% | – |
| `g35-ctx3k-fixed`（上限 3000，不可达） | 4 | 6 / 3 / 5 / 1 | 29.5 | 2 / 4 | 全部命中；每个压缩过的运行都记录了 `compaction_floor` |
| `g35-ctx12k`（上限 12000，可达） | 12 | 0–1 | 23.7（基线 22.6） | 5 / 12 | **1 条没中**：2 次运行压缩后仍高于阈值（9441、8857 > 8400），原因是保留的最近消息里有大段原始输出 |

结论只到机制层面：修复让压缩不再每步触发。通过率（41.7% 对基线 33%）在噪声之内，**不能**说压缩提升或损害了正确率，也没有测出摘要是否丢信息。

### 弱模型上的实验（Gemini 3.1-flash-lite，13 题 × 1 次）

| 条件 | 通过 | 假完成 | 说明 |
|---|---|---|---|
| 基线（`repeat 0`） | 3 / 13 | 7 / 10 | |
| 要求做规格验证的提示词 | 4 / 13 | 5 / 9 | 临时检查次数 6.0 → 7.5 / 次，行为几乎没变 |
| 开启思考（`thinkingLevel: high`） | 4 / 13 | 6 / 9 | 临时检查降到 0.3 / 次，步数 −15%，输出 token 翻倍 |

两者都只比基线多 1 题（赢 3 输 2），**在 13 题 × 1 次的样本下无法与噪声区分**；单次运行的噪声已经与这个差距相当。

## 目录结构

```
mini-agent/
├── miniagent/          # agent 主循环、工具、安全、压缩、轨迹、模型客户端、沙箱、录制回放
│   ├── eval/           # 评测 harness；view.py + viewer/index.html 是回放页；export.py 导出 SFT 数据
│   ├── mcp/            # MCP 笔记服务器、路径安全、客户端
│   └── taskgen/        # 变异式任务生成器（变异算子、测试拆分、PyPI 下载与安全解压）
├── configs/            # 评测配置（模型、协议、步数、提示词、价格表）
├── prompts/            # 实验用的系统提示词变体
├── tasks/              # 手写任务集（repo/ + hidden/ + solution/ + task.json），SPLIT.json，SUBSETS.json
├── seeds/              # 变异生成器的种子库（14 个 PyPI 小库 + 2 个手写），见 THIRD_PARTY.md
├── gen_tasks/          # 生成的任务（不提交，只提交 SPLIT.json 等，见其中的 README）
├── sandbox/            # 沙箱镜像的 Dockerfile
├── data/               # 导出的训练数据（不提交，只提交统计）
├── examples/           # 示例笔记（MCP 演示）和 MCP 配置
├── scripts/            # 辅助脚本（run_task.sh、mcp_demo.py、fetch_seeds.py / make_seeds.py、sft_mlx.py 训练、train_status.py 等）
├── tests/
├── docs/               # ablations.md、failure_cases.md、m4_design.md、m5_sandbox_taskgen_design.md、next_phase_plan.md
├── runs/               # 单次运行轨迹（本地生成，不提交）
├── results/            # 评测结果；只提交 report.md / summary.json / meta.json，原始轨迹不提交
├── models/ adapters/   # 模型权重和 LoRA 适配器（不提交）
└── PROJECT.md、LICENSE、THIRD_PARTY.md
```

## 设计要点

- **不用框架**：为了弄清框架到底封装了什么，以及每一层为什么这样设计。
- **轨迹格式优先**：每次运行都按统一格式落盘，评测归因、假完成检测和之后的回放都依赖它。
- **评测先于优化，且把测量基础设施的失败与被测系统的失败分开**：服务端限流、余额不足、配额耗尽都不计入模型的通过率。
- **预测先写后跑**：每个实验的预期写进配置，预测被推翻的也如实报告。

## 安全说明

agent 会执行模型生成的命令，存在风险：

- 危险命令黑名单只是**纵深防御**，容易被绕过（如通过解释器间接执行），不能当作安全边界。
- 文件工具限制在工作区内；不加 `--sandbox` 时 `bash` **不受**路径限制。
- 默认在宿主机直接执行命令；加 `--sandbox` 才会进容器（见上）。不加时请只在不含敏感数据的目录运行，用临时副本做评测（`run_task.sh` 与 harness 都是这样做的）。
- 使用第三方中转时，你的密钥和全部请求都会经过它。例如 `gemini-balance-lite` 会把选中的密钥完整写进函数日志；只用自己部署的实例和专用密钥。客户端不会把 `DEEPSEEK_API_KEY` 发给 DeepSeek 以外的主机。
- Gemini 免费档的输入输出可能被 Google 用于改进产品并被人工审阅（条款原文），不要用来处理私有代码。

## 已知局限

- MCP：协议实现是**对照规范手写**的，没有用官方客户端/SDK 做过互操作验证（这需要安装第三方依赖，尚未执行）；只做了 stdio 传输，没有 HTTP；只有工具能力，没有 resources / prompts。
- 只针对 coding 场景，其他场景未验证。
- **样本小**：每个条件 13 题 × 1～3 次。弱模型在 13 题 × 1 次下，小于约 35 个百分点的差距无法与噪声区分；强模型接近天花板时，5～8 点的差异也落在区间之内。还没有同一条件的重复基线来直接测噪声。
- **一个强模型 + 几个弱模型**：强模型的基线已饱和（约 90%），所以很多消融差异落在噪声内；弱模型的结果受免费档额度和服务端稳定性限制。
- 任务集是自建的，不是公开基准（SWE-bench 因磁盘空间未接入）；隐藏测试也出过缺陷（案例 10），已退役 2 题。
- **test 集（17 题）至今没有跑过**：它的用途是冻结配置后跑一次，得到一个没被我调参污染的数字；先看再改再重跑，它就变成了第二个 dev 集。
- **压缩修复的验证范围有限**：ctx3k 的表里数字来自修复之前的 DeepSeek 代码；修复在 Gemini 3.5-flash-lite 上验证了机制（4 + 12 次运行，预测 1 条没中），但样本太小，**摘要是否丢信息仍未测出**；DeepSeek 版配置因余额耗尽未跑。
- no-grep、no-verify-prompt 两个消融因余额耗尽未评估。
- **M5 的局限**:(1) 生成题是机械变异,比真实 bug 机械,且 DeepSeek 在 train 上几乎满分(513/514),轨迹形态单一(读 → 改一次 → 跑测试),基本没有"失败后纠正"的样本;(2) 种子库是知名开源库,学生模型预训练时可能见过原始代码,dev/test 的成绩可能被高估;(3) 可见测试里至少失败一个,所以"只能靠规格发现 bug"的难度没有覆盖,这与手写 B 层互补;(4) dev、test 各只有 2 个库,按库划分的好处是没有泄漏,代价是方差大;(5) 训练只用 ≤8192 token 的样本(65%),这是本机 16 GB 内存的限制;(6) 沙箱是容器,与宿主共享内核,不是虚拟机;(7) teacher 价格表的列对应关系未核对；(8) 学生的评测只有 dev 48 题、每题 1 次、温度 0，4/48 对 0/48 在统计上不显著，test 集没有跑，也没有重复运行去测噪声；(9) 训练只用了 152 条 ≤4096 token 的样本，客户端靠宽容解析才读得出工具调用（见上）；(10) 4/48 的基线依赖不稳定的工具调用标记，后续改成普通文本格式后通过数是 0/48，所有这些比较都是单次、温度 0、48 题，只能当作线索。
- **发布前提醒**:`results/` 和 `data/` 里有第三方模型(DeepSeek、Gemini、GLM)的输出。仓库不提交原始轨迹和训练数据(见 `.gitignore`);公开前请自行核对各家条款(例如 Gemini 对再分发和训练用途的限制)。

## 路线图

- [x] M1 最小 agent
- [x] M2 harness：任务格式、划分、隐藏测试、判分、报告、配对对比、断点续跑
- [x] M2 失败案例文档（15 条）、消融记录
- [x] 压缩触发加滞回（案例 2，有测试）
- [x] M2 收尾：压缩修复在 Gemini 3.5 上重跑（`g35-ctx3k-fixed`、`g35-ctx12k`），预测逐条核对
- [x] M3 回放与并排对比（未做按条件导出）
- [x] M4 MCP server 与越权测试（未做官方客户端互操作验证）
- [x] M5-a 确定性回放、Docker 沙箱(含逃逸测试)、变异式任务生成(352 题)
- [x] M5-b teacher 轨迹合成与 SFT 数据导出(510 条,只取 train)
- [x] M5-c LoRA 训练(前两次发散,第三次成功)
- [x] M5-d 前半:训练前后评测(dev)
- [x] M5-d 后续:edit_file 提示、缩短 old_string、普通文本工具调用格式(三轮均无通过数提升,见 docs/next_phase_plan.md)
- [ ] M5-d 后半:数据消融、一次 test、对照实验(只改 Adam 偏差修正)、切窗训练
- [ ] 上下文工程(可选):摘要 vs 结构化笔记

## 许可证

MIT
