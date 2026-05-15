# voice-ime 项目指南

## 项目定位

极简语音输入法：按住热键录音 → 端到端 ASR 识别 → 词表热词注入 → 剪贴板输出。

核心设计哲学：**链路极简 + 可切换后端**。ASR 层通过 Provider 模式封装三家（智谱/字节/阿里），默认智谱；词表从"运行时纠正"退化为"热词收集器"，ASR 调用时注入，不做二次处理。

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 录音 | `sounddevice` + `keyboard` | 按住 F9 录音，松手停止。Windows 需管理员权限运行 |
| ASR | 智谱 GLM-ASR-2512（默认）| OpenAI 兼容 multipart 接口，延迟 ~0.7s，¥0.06/分钟 |
| ASR（备选）| 字节 Seed-ASR 2.0 | HTTP 异步 + TOS 上传，延迟 ~1.3s，¥0.013/分钟 |
| ASR（备选）| 阿里 Qwen-Omni-Turbo | SSE 流式，延迟 ~1.0s，按 token 计费 |
| 输出 | `pyperclip` | 纯剪贴板，极简可靠 |
| 配置 | `.env` + `python-dotenv` | API Key、热键、模型参数集中管理 |

## 架构决策记录

### 为什么删除 LLM 后处理层？

- 端到端 ASR（智谱/字节）已经内置智能标点、ITN 数字转换、去冗余
- LLM 润色层带来延迟和幻觉风险，对"语音输入法"场景 ROI 为负
- 成熟方案里没有这一层，直接砍掉

### 为什么 glossary 从"运行时纠正"改为"热词收集器"？

- 端到端 ASR 支持 `hotwords` 参数直接注入术语，识别阶段就解决，不需要输出后再替换
- 保留 F10 反馈体验：用户一键把术语加入词表，下次 ASR 调用时自动作为 hotwords 注入
- glossary.json 格式保持不变（`{"错误写法": "正确术语"}`），但只取 values 作为热词

### 为什么保留字节/阿里 provider 死代码？

- 团队已决定用智谱，但 Provider 模式已建好，保留切换能力作为保险
- 未来如果智谱涨价/宕机/效果变差，改 `ASR_PROVIDER=` 即可切换，无需重写代码
- 维护成本可控（provider 代码稳定，接口变更频率低）

### 为什么用剪贴板而不是模拟键盘？

- `pynput` 模拟键盘输入中文有坑（受输入法状态干扰）
- 剪贴板 `Ctrl+V` 最稳，和系统输入法互不干扰
- 保持极简，不引入 GUI

## 目录结构

```
voice-ime/
├── main.py              # 主循环：热键监听 + 流水线调度
├── config.py            # 配置管理（ASR_PROVIDER + 各后端 Key + 热键 + 音频参数）
├── asr_provider.py      # 统一 ASR Provider（智谱/字节/阿里）
├── recorder.py          # 录音（sounddevice + keyboard）
├── glossary.py          # 热词收集器：F10 反馈沉淀术语，供 ASR hotwords 注入
├── output.py            # 剪贴板输出
├── upload_to_tos.py     # 火山引擎 TOS 文件上传（字节 ASR 需要）
├── requirements.txt
├── .env.example         # 配置模板
├── .gitignore           # 排除 .env / 临时录音 / IDE 配置
└── glossary.json        # 用户词表（运行时自动生成，不提交 git）
```

## 关键配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `ASR_PROVIDER` | `zhipu` | 后端选择：`zhipu` / `volcengine` / `ali` |
| `ZHIPU_API_KEY` | - | 智谱 API Key（ASR_PROVIDER=zhipu 时必填）|
| `VOLCENGINE_API_KEY` | - | 字节 API Key（ASR_PROVIDER=volcengine 时必填）|
| `TOS_ACCESS_KEY` / `TOS_SECRET_KEY` / `TOS_BUCKET` | - | 字节 ASR 上传音频到 TOS 需要 |
| `DASHSCOPE_API_KEY` | - | 阿里 API Key（ASR_PROVIDER=ali 时必填）|
| `HOTKEY_RECORD` | `f9` | 按住录音 |
| `HOTKEY_FEEDBACK` | `f10` | 反馈纠正，更新热词 |
| `GLOSSARY_PATH` | `glossary.json` | 词表文件路径 |

## 数据流

```
按住 F9 → recorder.py 录音 → 松手
  → asr_provider.py 识别（注入 glossary.hotwords()）
  → output.py 剪贴板输出

按 F10 → glossary.py 收集热词 → 保存 glossary.json
  → 下次 ASR 调用时 hotwords 自动注入
```

## 已知限制 / TODO

- [ ] 字节 Seed-ASR 的 WebSocket 实时流式版本（当前用 HTTP 轮询，延迟 ~1.3s）
- [ ] 反馈链路缺少"删除词表条目"功能
- [ ] 录音在 Python 3.14 上依赖 sounddevice，如不稳定建议降级到 3.11/3.12 + pyaudio
- [ ] 当前 ASR 只支持单文件识别，不支持实时流式（按住说话时边录边识别）

## 如何测试

```bash
# 1. 安装依赖
.venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置 .env（参考 .env.example）

# 3. 完整运行（需要麦克风 + 管理员权限）
python main.py
```

## 编码规范

- 最小改动原则，保持代码极简
- 所有中文输出避免 emoji（Windows GBK 控制台会乱码）
- 进度/耗时打印用 `[Module] 消息 (X.XXs)` 格式
- ASR Provider 新增后端时：继承 `BaseASRProvider`，实现 `transcribe(audio_path, **kwargs)`，返回统一格式 `{"text": str, "usage": dict, "provider": str, "latency": float, "raw": dict}`
