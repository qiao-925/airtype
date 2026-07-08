# airtype

> press a key. speak. words appear wherever your cursor is.

极简 Linux 全局语音输入法。快捷键触发 → 录音 → 本地 STT 推理 → 键盘输入。完全本地，零网络依赖。

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/qiao-925/airtype/master/install.py | python3
```

安装过程选择 SenseVoice-Small 模型量化等级即可。

## 快捷键绑定

绑定桌面快捷键到 `airtype` 命令，推荐 `Alt+V`。

```
按 Alt+V → ● listening（开始录音）
  ├─ 说话
  └─ 再按 Alt+V → 文字出现在光标位置
```

## 运行流程

```
快捷键
  ↓
airtype (Python, ~430 行)
  ├─ ① rec (sox)            → 16kHz mono WAV 录音
  ├─ ② SenseVoice.cpp       → 本地 STT 推理（含 ITN 标点）
  ├─ ③ regex                → 多段文本解析 + 控制字符清理
  ├─ ④ 规则后处理            → 去填充词、去重复、自我纠正、补标点、格式化列表
  └─ ⑤ wtype                → 逐字键盘输入（10字/批，防浏览器跳转）
  │
  └─ ⑥ voice-overlay (C, ~224 行) → SDL2 状态 pill
```

## 后处理规则

纯规则实现，零模型依赖、零延迟、零磁盘开销：

| 规则 | 效果 | 示例 |
|------|------|------|
| 去填充词 | 去除"嗯、啊、那个、就是说、你知道的、对吧、对不对" | `嗯那个我们开会` → `我们开会` |
| 去重复 | 合并连续重复字词 | `今天今天天气不错不错` → `今天天气不错` |
| 自我纠正 | 句首"不对/不是/错了"等纠正标记，跳过前文 | `明天不对后天开会` → `后天开会` |
| 格式化列表 | 第一步/第二步 / 首先/然后/最后 自动编号 | `第一步打开设置第二步点击关于` → `1.打开设置；2.点击关于` |
| 补标点 | 疑问句加？陈述句加。 | `这个方案怎么样` → `这个方案怎么样？` |

## 配置

`~/.local/share/airtype/config`

```ini
MODEL="sense-voice-small-q8_0.gguf"
MAX_SECONDS=3600
LANG="zh"
THREADS=4
```

## 日志

`tail -f ~/.local/share/airtype/airtype.log`

## 测试

```bash
python3 tests/test_config.py    # 配置解析 + 规则后处理测试
python3 tests/test_asr.py       # ASR 策略函数测试
```

## Ack

- [SenseVoice.cpp](https://github.com/lovemefan/SenseVoice.cpp) — ASR 引擎
- [SDL2](https://www.libsdl.org/) — 跨平台图形
- [stb_truetype](https://github.com/nothings/stb) — 字体光栅化

## License

MIT
