# 04 · `miniagent/client.py`:和模型对话的 HTTP 客户端

**作用**:把"消息列表 + 工具说明书"通过 HTTP 发给 DeepSeek 的 `/chat/completions` 接口,把返回的 JSON 整理成项目内部用的简单对象。只用标准库,没有第三方依赖。

先建立直觉:调用大模型 API,本质就是**发一个 HTTP POST 请求,请求体是 JSON,响应体也是 JSON**。

请求大致长这样:
```json
{"model": "deepseek-chat", "max_tokens": 4096,
 "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "修 bug"}],
 "tools": [{"type": "function", "function": {...}}]}
```
响应里我们关心的部分:
```json
{"choices": [{"finish_reason": "tool_calls",
              "message": {"content": null,
                          "tool_calls": [{"id": "call_1", "type": "function",
                                          "function": {"name": "grep", "arguments": "{\"pattern\": \"def\"}"}}]}}],
 "usage": {"prompt_tokens": 120, "completion_tokens": 20, "prompt_cache_hit_tokens": 100},
 "model": "deepseek-chat"}
```
注意 `arguments` 是**字符串**(里面是 JSON),不是对象——后面 `agent.py` 才解析它。

## 第 1–14 行:导入与常量

- `urllib.request` / `urllib.error`:标准库里发 HTTP 请求和处理 HTTP 错误的模块。
- `DEFAULT_BASE_URL`:默认接口地址。
- `_RETRY_STATUS = {429, 500, 502, 503, 504}`:遇到这些状态码值得重试(429 = 请求太频繁,5xx = 服务端暂时出问题)。

## 第 17–18 行:`APIError`

自定义异常,所有"调用 API 失败"都抛它。

## 第 21–25 行:`ToolCall`

模型的一次"工具调用请求":`id`(调用编号,回传结果时要对上)、`name`(工具名)、`arguments`(原样保留的 JSON 字符串)。

## 第 28–34 行:`ModelResponse`

整理后的模型回复:
- `text`:模型说的话(可能为空串)。
- `tool_calls`:想调用的工具列表(可能为空列表)。
- `finish_reason`:为什么停:`stop` 正常说完,`tool_calls` 要调工具,`length` 被 `max_tokens` 截断。
- `usage`:token 用量字典。
- `model`:服务器报告实际用的模型名(默认空串)。

`agent.py` 只依赖这个对象,不关心底层是哪家 API。

## 第 37–45 行:`ChatClient.__init__`

- 第 40 行 `api_key or os.environ.get("DEEPSEEK_API_KEY", "")`:优先用传入的 key,否则读环境变量;都没有得到 `""`。
- 第 41–42 行:没 key 就抛 `APIError`(CLI 会捕获并友好提示)。
- 第 43 行:`base_url` 同理按"参数 → 环境变量 → 默认值"的顺序取,`.rstrip("/")` 去掉末尾斜杠,避免拼出 `//chat/completions`。
- 第 44–45 行:超时(秒)和最大重试次数。

## 第 47–74 行:`chat`

- 签名里的 `*`:后面的参数**必须**用关键字传,如 `client.chat(model="x", messages=[...])`,避免位置传参搞混顺序。
- 第 50–54 行 构造请求体 `body`:
  - `([{"role": "system", ...}] if system else []) + messages`:有系统提示词就在列表最前面放一条 system 消息,然后把 `+` 把两个列表拼接。
  - 系统提示词(system prompt)不是 `messages` 的一部分,而是由这里在发送时放到最前面,所以 `agent.py` 的压缩逻辑不用考虑它。
- 第 55–58 行:只有传了工具才带 `tools`;传了 `temperature` 才带。`temperature` 控制随机性,评测时要固定。
- 第 59 行 `self._post("/chat/completions", body)`:发请求,拿到解析后的字典。
- 第 60–64 行:取 `choices[0].message`;结构不对(`KeyError`、`IndexError`、`TypeError`)就抛带原始内容片段的 `APIError`,便于排查。
- 第 65–66 行:列表推导,把原始 `tool_calls` 转成 `ToolCall` 对象。
  - `msg.get("tool_calls") or []`:API 不带这个字段或为 `null` 时当作空列表。
  - `c["function"].get("arguments") or "{}"`:没有参数时用 `"{}"`(空对象)。
- 第 67–72 行:整理 token 用量。`u.get("prompt_tokens", 0) or 0` 里的 `or 0` 防的是值为 `None` 的情况。
  - `prompt_tokens` 已**包含**命中缓存的部分;`prompt_cache_hit_tokens` 是其中命中缓存的数量(缓存命中更便宜,评测算成本时要分开)。
- 第 73–74 行:返回 `ModelResponse`。`msg.get("content") or ""` 保证 `text` 一定是字符串。

## 第 76–96 行:`_post`(发送 + 重试)

- 第 77–80 行:构造 `Request`:地址、请求体(`json.dumps(...).encode("utf-8")` 转成字节)、`method="POST"`、请求头(`Content-Type` 声明 JSON;`Authorization: Bearer <key>` 是鉴权)。
- 第 81 行 `for attempt in range(self.retries + 1):`:总共尝试 `retries + 1` 次(首次 + 重试)。
- 第 83–84 行 `with urllib.request.urlopen(req, timeout=...) as r:`:发请求;成功就读取响应字节、解码、`json.loads` 变成字典并 `return`。
- 第 85–90 行 `except urllib.error.HTTPError`:服务器返回了错误状态码。
  - 读错误信息的前 500 字符(`"replace"` 让无法解码的字节变成占位符,不抛异常)。
  - 状态码可重试且还有次数 → `time.sleep(2 ** attempt)` 等 1、2、4 秒再试(**指数退避**,避免连续猛敲);`continue` 进入下一轮。
  - 否则抛 `APIError`。
- 第 91–95 行 `except (URLError, TimeoutError)`:网络层问题(断网、超时),同样重试。
  - 顺序很重要:`HTTPError` 是 `URLError` 的子类,必须先写 `HTTPError`,否则会被后面的 `URLError` 提前接住。
- 第 96 行:理论上走不到的兜底,保证函数不会隐式返回 `None`。

## 它在项目里的位置

- `agent.py` 调 `client.chat(...)`。
- 测试里用"假客户端"(只要有个 `chat` 方法、返回 `ModelResponse`)替换它,不联网也能测整个循环——这就是 `agent.py` 里 `client: object` 的设计意图。
