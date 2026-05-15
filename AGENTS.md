# voice-ime 项目指南

## 项目定位

极简语音输入法：按住热键录音 → 阿里云 ASR 识别 → 本地词表纠正 → LLM 润色 → 剪贴板输出。

核心设计哲学：**分层解耦 + 本地词表优先**。ASR、词表、LLM 三层可以独立替换/优化。

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 录音 | `sounddevice` + `keyboard` | 按住 F9 录音，松手停止。Windows 需管理员权限运行 |
| ASR | 阿里云 DashScope `paraformer-v2` | 录音文件识别，中文效果优秀，0.00008 元/秒 |
| LLM | OpenAI 兼容接口 | 当前配的是豆包 (doubao-seed-2-0-lite)，可任意替换 |
| 输出 | `pyperclip` | 纯剪贴板，极简可靠 |
| 配置 | `.env` + `python-dotenv` | API Key、热键、模型参数集中管理 |

## 架构决策记录

### 为什么用剪贴板而不是模拟键盘？

- `pynput` 模拟键盘输入中文有坑（受输入法状态干扰）
- 剪贴板 `Ctrl+V` 最稳，和系统输入法互不干扰
- 保持极简，不引入 GUI

### 为什么词表做两层纠正？

1. **本地前向最大匹配**：零成本、确定性、隐私性好，解决"已知错误"
2. **LLM Prompt 注入**：智能处理变体和上下文，解决"未知错误"

### 为什么 ASR 用 paraformer-v2 而不是 fun-asr？

- paraformer-v2 便宜 2.75 倍（0.00008 vs 0.00022 元/秒）
- 录音文件识别两者都没有延迟 SLA，速度不是决策因素
- fun-asr 支持热词，但 paraformer-v2 + 本地词表已够用

### 为什么 LLM Prompt 抽离到 md 文件？

- `prompts/llm_postprocess.md` 可随时调整，无需改代码
- 方便非技术人员参与 prompt 调优

## 目录结构

```
voice-ime/
├── main.py                  # 主循环：热键监听 + 流水线调度
├── config.py                # 配置管理
├── recorder.py              # 录音（sounddevice + keyboard）
├── asr.py                   # 阿里云 DashScope ASR
├── glossary.py              # 词表管理（加载/保存/纠正/Prompt生成）
├── llm_postprocess.py       # LLM 润色（Prompt 从 md 文件读取）
├── output.py                # 剪贴板输出
├── test_with_file.py        # 用本地音频文件测试完整链路
├── prompts/
│   └── llm_postprocess.md   # LLM System Prompt
├── glossary.json            # 用户词表（运行时自动生成）
├── .env                     # API Key 等敏感配置（不提交 git）
├── .env.example             # 配置模板
└── requirements.txt
```

## 关键配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DASHSCOPE_API_KEY` | - | 阿里云语音识别（必填） |
| `LLM_API_KEY` | - | LLM 接口（不填则跳过 LLM 后处理） |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址 |
| `HOTKEY_RECORD` | `f9` | 按住录音 |
| `HOTKEY_FEEDBACK` | `f10` | 反馈纠正，更新词表 |
| `GLOSSARY_PATH` | `glossary.json` | 词表文件路径 |

## 已知限制 / TODO

- [ ] 阿里云热词前置（fun-asr / phrase_id 方案），待评估后实施
- [ ] 反馈链路选项 1 粒度太粗（整句映射），建议后续做智能 diff 提取最小变化子串
- [ ] 反馈链路缺少"删除词表条目"功能
- [ ] 录音在 Python 3.14 上依赖 sounddevice，如不稳定建议降级到 3.11/3.12 + pyaudio

## 如何测试

```bash
# 1. 安装依赖
.venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置 .env（参考 .env.example）

# 3. 用本地音频文件测试（无需麦克风）
python test_with_file.py ..\dm-agent\output_audio_cn\001_DM_1770706761.mp3

# 4. 完整运行（需要麦克风 + 管理员权限）
python main.py
```

## 编码规范

- 最小改动原则，保持代码极简
- 所有中文输出避免 emoji（Windows GBK 控制台会乱码）
- 进度/耗时打印用 `[Module] 消息 (X.XXs)` 格式
- Prompt 改动走 `prompts/*.md` 文件，不走代码
