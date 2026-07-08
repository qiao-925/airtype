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

## 日志

`tail -f ~/.local/share/airtype/airtype.log`

## Ack

- [SenseVoice.cpp](https://github.com/lovemefan/SenseVoice.cpp) — ASR 引擎
- [SDL2](https://www.libsdl.org/) — 跨平台图形
- [stb_truetype](https://github.com/nothings/stb) — 字体光栅化

## License

MIT
