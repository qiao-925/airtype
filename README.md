# airtype

> press a key. speak. words appear wherever your cursor is.

极简 Linux 全局语音输入法。快捷键触发 → 录音 → 本地 STT 推理 → 键盘输入。完全本地，零网络依赖。

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/qiao-925/airtype/master/install.py | python3
```

## 快捷键绑定

绑定桌面快捷键到 `airtype` 命令，推荐 `Alt+V`。

```
按 Alt+V → ● listening（开始录音）
  ├─ 说话
  └─ 再按 Alt+V → 文字出现在光标位置
```

## 日志

`tail -f ~/.local/share/airtype/airtype.log`

## 运行流程

```
快捷键
  ↓
airtype (Python, ~230 行)
  ├─ ① rec (sox)            → 16kHz mono WAV 录音
  ├─ ② sense-voice-main     → SenseVoice.cpp 本地推理
  ├─ ③ regex                → 多段文本解析拼接
  └─ ④ wtype                → 键盘输入
  │
  └─ ⑤ voice-overlay (C, ~224 行) → SDL2 状态 pill
```

## Ack

- [SenseVoice.cpp](https://github.com/lovemefan/SenseVoice.cpp) — STT 引擎
- [SDL2](https://www.libsdl.org/) — 跨平台图形
- [stb_truetype](https://github.com/nothings/stb) — 字体光栅化

## License

MIT
