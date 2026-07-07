# airtype

> press a key. speak. words appear wherever your cursor is.

极简 Linux 全局语音输入法。快捷键触发 → 录音 → 本地 STT 推理 → 键盘输入。完全本地，零网络依赖。

## 特性

- **可插拔 ASR 引擎**：SenseVoice / Qwen3-ASR / Fun-ASR-Nano，配置切换
- **后处理润色**：可选 Qwen3.5 LLM 对识别结果做纠错、去语气词、补标点
- **极简部署**：单 config 文件驱动，安装脚本自动编译和下载
- **完全本地**：所有推理在本地 CPU/GPU 完成，零网络依赖

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/qiao-925/airtype/master/install.py | python3
```

安装过程中会依次选择：
1. ASR 语音识别引擎
2. ASR 模型量化等级
3. 后处理润色模型（可跳过）

## 快捷键绑定

绑定桌面快捷键到 `airtype` 命令，推荐 `Alt+V`。

```
按 Alt+V → ● listening（开始录音）
  ├─ 说话
  └─ 再按 Alt+V → 文字出现在光标位置
```

## 配置

配置文件位于 `~/.local/share/airtype/config`，修改后下次运行生效。

```ini
# ASR 语音识别引擎: sensevoice | qwen3asr | funasr
ASR_ENGINE="sensevoice"
MODEL="sense-voice-small-q5_k.gguf"
MAX_SECONDS=3600
LANG="zh"
THREADS=4

# 后处理润色模型（留空则跳过）
REFINE_MODEL="Qwen3.5-0.8B-Q4_K_M.gguf"
REFINE_THREADS=4
```

### ASR 引擎

| 引擎 | 配置值 | 特点 | 延迟（10s 音频） |
|------|--------|------|-----------------|
| **SenseVoice** | `sensevoice` | 速度最快，5 种语言 | ~0.5s |
| **Qwen3-ASR** | `qwen3asr` | 准确率高，52 语言，22 种方言 | ~2s |
| **Fun-ASR-Nano** | `funasr` | 方言支持好，官方 llama.cpp runtime | ~5s |

### 后处理模型

| 模型 | 大小 | 延迟 | 备注 |
|------|------|------|------|
| Qwen3.5-0.8B | ~500 MB | 2-4s | ★ 推荐，轻量 |
| Qwen3.5-2B | ~1.2 GB | 4-10s | 更强纠错 |

## 运行流程

```
快捷键
  ↓
airtype (Python, ~300 行)
  ├─ ① rec (sox)            → 16kHz mono WAV 录音
  ├─ ② ASR 引擎              → 语音识别（可插拔）
  │     ├─ SenseVoice.cpp
  │     ├─ transcribe.cpp
  │     └─ llama-funasr-cli
  ├─ ③ regex                → 多段文本解析拼接
  ├─ ④ llama-cli (可选)     → Qwen3.5 后处理润色
  └─ ⑤ wtype / clipboard    → 键盘输入
  │
  └─ ⑥ voice-overlay (C, ~224 行) → SDL2 状态 pill
```

## 日志

`tail -f ~/.local/share/airtype/airtype.log`

## 测试

```bash
python3 tests/test_config.py    # 配置解析测试
python3 tests/test_asr.py       # ASR 策略函数测试
```

## 目录结构

```
~/.local/share/airtype/
  config                              # 配置文件
  airtype.log                         # 运行日志
  voice-overlay                       # 状态 overlay
  SenseVoice.cpp/build/bin/           # ASR 引擎: SenseVoice
  transcribe.cpp/build/bin/           # ASR 引擎: Qwen3-ASR
  Fun-ASR/runtime/llama.cpp/build/bin/ # ASR 引擎: Fun-ASR-Nano
  llama.cpp/build/bin/                # 后处理 LLM 引擎
  models/                             # 模型文件（GGUF）
```

## Ack

- [SenseVoice.cpp](https://github.com/lovemefan/SenseVoice.cpp) — SenseVoice ASR 引擎
- [transcribe.cpp](https://github.com/handy-computer/transcribe.cpp) — Qwen3-ASR 引擎
- [Fun-ASR](https://github.com/FunAudioLLM/Fun-ASR) — Fun-ASR-Nano 引擎
- [llama.cpp](https://github.com/ggml-org/llama.cpp) — 后处理 LLM 引擎
- [SDL2](https://www.libsdl.org/) — 跨平台图形
- [stb_truetype](https://github.com/nothings/stb) — 字体光栅化

## License

MIT
