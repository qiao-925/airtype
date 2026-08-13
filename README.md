# airtype

> press a key. speak. words appear wherever your cursor is.

极简 Linux 全局语音输入法。快捷键触发 → 录音 → 本地 STT 推理 → 键盘输入。完全本地，零网络依赖。

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/qiao-925/airtype/master/install.py | python3
```

## 发行版支持

一键安装脚本已适配的发行版系列（状态随实测持续更新）：

| 发行版系列 | 状态 | 说明 |
|---|---|---|
| Debian / Ubuntu（含 Pop!_OS） | ✅ 完整支持 | 开发与验证基准 |
| Arch Linux（CachyOS / Manjaro / EndeavourOS） | ✅ 支持 | 依赖包名已适配，待各发行版实测 |
| Fedora / RHEL / CentOS | 🚧 实验性 | 依赖包名已修正，尚未完整验证 |
| openSUSE | ❌ 未支持 | 尚未适配 zypper |
| Alpine Linux | ❌ 未支持 | 未适配 apk，且依赖 glibc 生态 |

> 文本注入：优先 **ydotool**（基于 `/dev/uinput`，任意合成器可用，支持任意 Unicode，需
> `ydotoold` 守护进程）；回退 **wtype**（基于虚拟键盘协议，仅 Sway / Hyprland / River 等
> wlroots 合成器可用，**KDE / GNOME 不实现该协议**）。X11 会话尚未支持直接输入（可先配合
> `--clipboard` 使用）。


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
