# voice-ime

极简语音输入法：录音 → 端到端 ASR → 词表纠正 → LLM 润色 → 复制到剪贴板。

支持三家国内 LLM-based 端到端 ASR 提供商一键切换：**智谱（默认）**、字节、阿里。

## 特性

- 🎙️ **按住即录**：默认按住 `F9` 录音，松开后自动识别
- ☁️ **多 ASR 后端**：智谱 GLM-ASR / 字节 Seed-ASR / 阿里 Qwen-Omni 一键切换
- 📖 **专业词表**：两层纠正机制
  1. **字符串前向最大匹配**：快速、确定性的术语替换
  2. **LLM Prompt 注入**：让模型在润色时参考词表
- 🤖 **LLM 后处理**：可配置任意 OpenAI 兼容接口，自动加标点、去冗余、纠术语
- 🔄 **词表自学习**：按 `F10` 进入反馈模式，把纠正经验沉淀到 `glossary.json`
- 📋 **剪贴板输出**：识别完成后直接复制到剪贴板，手动粘贴即可

## 快速开始

```bash
# 1. 创建虚拟环境并安装依赖
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env，选择 ASR 提供商并填入对应 Key

# 3. 运行
python main.py
```

### .env 配置示例

```bash
# === 选择 ASR 提供商 ===
ASR_PROVIDER=zhipu          # 可选: zhipu | volcengine | ali

# === 智谱 GLM-ASR（默认推荐）===
ZHIPU_API_KEY=your-zhipu-key

# === 字节 Seed-ASR（性价比最高）===
# VOLCENGINE_API_KEY=your-volc-key
# TOS_ACCESS_KEY=your-tos-ak
# TOS_SECRET_KEY=your-tos-sk
# TOS_BUCKET=your-bucket

# === 阿里 Qwen-Omni（多模态扩展）===
# DASHSCOPE_API_KEY=sk-xxx
# ALI_ASR_MODEL=qwen-omni-turbo
```

## 用法

| 操作 | 说明 |
|------|------|
| 按住 `F9` | 开始录音，松开后自动进行识别、纠正、润色并输出 |
| 按 `F10` | 对最近一次结果进行反馈，更新专业词表 |

## ASR 提供商对比

我们使用同一批 D&D 跑团中文语音（MiniMax TTS 合成，6 段，总长 24 秒）对三家端到端 ASR 进行了横向评测。

### 识别质量

| 文件 | Ground Truth | 字节 Seed-ASR | 智谱 GLM-ASR | 阿里 Qwen-Omni |
|---|---|---|---|---|
| 001 | `梅菲斯特，你现在要做什么？` | `梅菲斯特，你现在要做什么？` | `梅菲斯特，你现在要做什么？` | `梅菲斯特你现在要做什么？` |
| 002 | `我要往后走三十尺，然后释放火球术！` | `我要往后走30尺，然后释放火球术。` | `我要往后走30尺，然后释放火球术。` | `我要往后走三十尺然后释放火球术` |
| 003 | `好的，你需要进行专注检定...` | `好的，你需要进行专注检定...` | `好的，你需要进行专注检定...` | `好的你需要进行专注检定因为有一只地精正在你的身边干扰你` |
| 004 | `没问题，我的体质豁免很高。我投掷出了... 18点！` | `没问题，我的体质豁免很高，我投掷出了18点。` | `没问题，我的体质豁免很高，我投掷出了18点。` | `没问题我的体质豁免很高我投掷出了十八点` |
| 005 | `那我也要在旁边协助攻击，我使用借机攻击！` | `那我也要在旁边协助攻击，我使用借机攻击。` | `那我也要在旁边协助攻击，我使用借机攻击。` | `那我也要在旁边协助攻击我使用借机攻击` |
| 006 | `很好，战斗开始了。` | `很好，战斗开始了。` | `很好，战斗开始了。` | `很好战斗开始了` |

**语义准确率**：三家均为 **100%**，D&D 术语（火球术、专注检定、体质豁免、借机攻击）零错误。

### 功能差异

| 维度 | 字节 Seed-ASR 2.0 | 智谱 GLM-ASR-2512 | 阿里 Qwen-Omni-Turbo |
|---|---|---|---|
| **智能标点** | ✅ 支持 | ✅ 支持 | ❌ 无标点 |
| **ITN 数字转换** | ✅ 三十尺→30尺 | ✅ 三十尺→30尺 | ❌ 保持原文 |
| **Prompt 注入** | ✅ `corpus.context` | ✅ `prompt` 参数 | ⚠️ system_prompt 易幻觉 |
| **热词支持** | ✅ `hotwords` 嵌套在 context 内 | ✅ `hotwords` 数组参数 | ❌ 无原生热词接口 |
| **延迟（2.7s 音频）** | ~1.3s | **~0.7s** | ~1.0s |
| **价格** | **¥0.013/分钟** | ¥0.06/分钟 | ¥0.025/千 token 音频 |
| **接口复杂度** | 中（需 TOS + 轮询） | **低**（multipart 直传） | 中（SSE 流式解析） |

### 选型建议

| 场景 | 推荐 |
|---|---|
| **追求低延迟** | 智谱（0.7s，体验最流畅） |
| **追求性价比** | 字节（¥0.013/分钟，价格最低） |
| **追求接入简单** | 智谱（OpenAI 兼容，一行代码） |
| **需要多模态扩展**（后续加视频/图片理解） | 阿里 Qwen-Omni |
| **需要强 Prompt/热词控制** | 字节或智谱 |
| **voice-ime 默认** | **智谱**（团队内部采用） |

### 接入注意事项

- **字节 Seed-ASR**：录音文件识别需要音频有公网 URL。Demo 中通过火山引擎 TOS 上传本地文件获取 URL。`hotwords` 必须嵌套在 `corpus.context` JSON 字符串内部（`{"hotwords":[{"word":"xxx"}]}`），不能作为 `corpus` 的独立字段。
- **智谱 GLM-ASR**：OpenAI 兼容接口，multipart 直接上传本地文件即可。`prompt` 用于连续识别上下文衔接，`hotwords` 为数组格式。
- **阿里 Qwen-Omni**：是多模态**对话模型**而非纯 ASR 模型，`system_prompt` 容易导致幻觉（编造内容）。纯 ASR 场景建议留空 `system_prompt`，仅用 `user_prompt` 明确指示"忠实转写"。音频输入必须用 `input_audio` 类型，且必须开启 `stream=True`。

## 词表机制

词表文件 `glossary.json` 格式：

```json
{
  "马克拉夫": "Markov",
  "派森": "Python",
  "杰森": "JSON"
}
```

- **自动加载**：启动时自动加载
- **前向最大匹配**：ASR 结果出来后先做纯字符串替换
- **Prompt 注入**：替换后的文本送给 LLM 时，词表也会写入 system/user prompt
- **反馈更新**：如果某次识别错误，按 `F10` 把正确映射写回词表，下次识别优先命中

## 项目结构

```
voice-ime/
├── main.py                # 主循环（热键监听 + 流水线调度）
├── config.py              # 配置管理（.env + 默认值）
├── asr_provider.py        # 统一 ASR 接口封装（智谱/字节/阿里）
├── recorder.py            # 录音（pyaudio + keyboard）
├── glossary.py            # 专业词表：加载、保存、字符串纠正、Prompt 生成
├── llm_postprocess.py     # LLM 润色（OpenAI 兼容接口）
├── output.py              # 输出到剪贴板
├── upload_to_tos.py       # 火山引擎 TOS 文件上传（字节 ASR 需要）
├── demo_glm_asr.py        # 智谱 GLM-ASR Demo
├── demo_seed_asr.py       # 字节 Seed-ASR Demo
├── demo_qwen_omni_asr.py  # 阿里 Qwen-Omni Demo
├── benchmark_latency.py   # 三家延迟对比测试
├── requirements.txt
├── .env.example
└── glossary.json          # 用户词表（运行时自动生成）
```

## 参考来源

- 阿里云 ASR 调用参考自 `./dm-agent/voice-bridge/voice_bridge.py`
- 字节 Seed-ASR 2.0 文档: https://www.volcengine.com/docs/6561/1354868
- 智谱 GLM-ASR-2512 文档: https://docs.bigmodel.cn/cn/guide/models/sound-and-video/glm-asr-2512
- 阿里 Qwen-Omni 文档: https://help.aliyun.com/zh/model-studio/user-guide/qwen-omni
