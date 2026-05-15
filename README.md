# voice-ime

极简语音输入法：按住热键录音 → 端到端 ASR 识别 → 词表热词注入 → 剪贴板输出。

默认使用 **智谱 GLM-ASR-2512**，一键切换字节 Seed-ASR / 阿里 Qwen-Omni。

## 特性

- 🎙️ **按住即录**：默认按住 `F9` 录音，松开后自动识别并输出到剪贴板
- ☁️ **多 ASR 后端**：智谱（默认）/ 字节 / 阿里一键切换，改 `.env` 即可
- 📖 **热词自学习**：按 `F10` 把识别错误的术语加入词表，下次 ASR 自动注入 hotwords
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

# === 智谱 GLM-ASR（默认推荐，延迟最低）===
ZHIPU_API_KEY=your-zhipu-key

# === 字节 Seed-ASR（性价比最高，需 TOS）===
# VOLCENGINE_API_KEY=your-volc-key
# TOS_ACCESS_KEY=your-tos-ak
# TOS_SECRET_KEY=your-tos-sk
# TOS_BUCKET=your-bucket

# === 阿里 Qwen-Omni（多模态扩展）===
# DASHSCOPE_API_KEY=sk-xxx
# ALI_ASR_MODEL=qwen-omni-turbo

# === 热键 ===
HOTKEY_RECORD=f9
HOTKEY_FEEDBACK=f10
```

## 用法

| 操作 | 说明 |
|------|------|
| 按住 `F9` | 开始录音，松开后自动识别并输出到剪贴板 |
| 按 `F10` | 对最近一次结果进行反馈，把术语加入热词表 |

## ASR 提供商对比

同一批 D&D 跑团中文语音（MiniMax TTS 合成，6 段）横向评测：

| 文件 | Ground Truth | 字节 Seed-ASR | 智谱 GLM-ASR | 阿里 Qwen-Omni |
|---|---|---|---|---|
| 001 | `梅菲斯特，你现在要做什么？` | `梅菲斯特，你现在要做什么？` | `梅菲斯特，你现在要做什么？` | `梅菲斯特你现在要做什么？` |
| 002 | `我要往后走三十尺，然后释放火球术！` | `我要往后走30尺，然后释放火球术。` | `我要往后走30尺，然后释放火球术。` | `我要往后走三十尺然后释放火球术` |
| 003 | `好的，你需要进行专注检定...` | `好的，你需要进行专注检定...` | `好的，你需要进行专注检定...` | `好的你需要进行专注检定因为有一只地精正在你的身边干扰你` |
| 004 | `没问题，我的体质豁免很高。我投掷出了... 18点！` | `没问题，我的体质豁免很高，我投掷出了18点。` | `没问题，我的体质豁免很高，我投掷出了18点。` | `没问题我的体质豁免很高我投掷出了十八点` |
| 005 | `那我也要在旁边协助攻击，我使用借机攻击！` | `那我也要在旁边协助攻击，我使用借机攻击。` | `那我也要在旁边协助攻击，我使用借机攻击。` | `那我也要在旁边协助攻击我使用借机攻击` |
| 006 | `很好，战斗开始了。` | `很好，战斗开始了。` | `很好，战斗开始了。` | `很好战斗开始了` |

### 功能差异

| 维度 | 字节 Seed-ASR 2.0 | 智谱 GLM-ASR-2512 | 阿里 Qwen-Omni-Turbo |
|---|---|---|---|
| **智能标点** | ✅ | ✅ | ❌ |
| **ITN 数字转换** | ✅ 三十尺→30尺 | ✅ 三十尺→30尺 | ❌ 保持原文 |
| **Prompt 注入** | ✅ `corpus.context` | ✅ `prompt` 参数 | ⚠️ 易幻觉 |
| **热词支持** | ✅ 嵌套在 context 内 | ✅ `hotwords` 数组 | ❌ |
| **延迟（2.7s 音频）** | ~1.3s | **~0.7s** | ~1.0s |
| **价格** | **¥0.013/分钟** | ¥0.06/分钟 | ¥0.025/千 token 音频 |
| **接口复杂度** | 中（TOS + 轮询） | **低**（multipart 直传）| 中（SSE 流式）|

### 选型建议

| 场景 | 推荐 |
|---|---|
| **低延迟 + 接入简单** | 智谱（0.7s，OpenAI 兼容） |
| **性价比优先** | 字节（¥0.013/分钟） |
| **多模态扩展**（后续加视频/图片） | 阿里 Qwen-Omni |
| **voice-ime 默认** | **智谱** |

## 词表机制（热词收集器）

`glossary.json` 格式保持不变：

```json
{
  "火球数": "火球术",
  "体质勉疫": "体质豁免",
  "借机工击": "借机攻击"
}
```

- **F10 反馈**：识别错误时按 `F10`，输入"错误写法 → 正确热词"，自动保存
- **自动注入**：下次 ASR 调用时，所有 `values` 去重后作为 `hotwords` 注入模型
- **追溯记录**：`key` 保留历史错误写法，方便追溯哪些词容易识别错

> 旧版 voice-ime 在 ASR 输出后做字符串前向匹配替换，新版改为 ASR 调用时注入 hotwords，模型内部优先识别，链路更干净。

## 项目结构

```
voice-ime/
├── main.py              # 主循环（热键监听 + 流水线调度）
├── config.py            # 配置管理（ASR_PROVIDER + Key + 热键 + 音频）
├── asr_provider.py      # 统一 ASR 接口封装（智谱/字节/阿里）
├── recorder.py          # 录音（sounddevice + keyboard）
├── glossary.py          # 热词收集器（F10 反馈 → hotwords 注入 ASR）
├── output.py            # 剪贴板输出
├── upload_to_tos.py     # 火山引擎 TOS 上传（字节 ASR 需要）
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── AGENTS.md
└── glossary.json        # 用户热词（运行时自动生成，不提交 git）
```

## 参考来源

- 阿里云 ASR 调用参考自 `./dm-agent/voice-bridge/voice_bridge.py`
- 字节 Seed-ASR 2.0 文档: https://www.volcengine.com/docs/6561/1354868
- 智谱 GLM-ASR-2512 文档: https://docs.bigmodel.cn/cn/guide/models/sound-and-video/glm-asr-2512
- 阿里 Qwen-Omni 文档: https://help.aliyun.com/zh/model-studio/user-guide/qwen-omni
