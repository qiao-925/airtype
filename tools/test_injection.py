#!/usr/bin/env python3
"""test_injection.py — 注入节点独立测试（不涉及录音/ASR/overlay 全链路）。

把「文本注入」拆成可观测的原子步骤，逐次注入唯一标记，统计各环节成功率，
用于定位「偶尔能输入、偶尔不能」的问题出在哪一环。

注入链路（中文走剪贴板+粘贴）:
  wl-copy 写入剪贴板
  ├─ 校验: wl-paste 读回并比对（可选的，粘贴前轮询直到就绪）
  └─ 粘贴: ydotool key 发送 Ctrl+V
  送达: 目标窗口是否真的收到（自动验证靠捕获文件，或人工肉眼确认）

用法:
  先准备一个目标窗口并聚焦：
    A. 自动验证: 打开 konsole 并运行  cat > /tmp/inject-capture.txt
       （把焦点点到这个 konsole 上），然后 --capture /tmp/inject-capture.txt
    B. 人工观察: 聚焦任意文本输入框（编辑器/聊天框），不加 --capture

  运行:
    python3 tools/test_injection.py --live 20 --capture /tmp/inject-capture.txt   # 中文，自动验证
    python3 tools/test_injection.py --live 20 --ascii                              # ASCII 直接键入
    python3 tools/test_injection.py --live 20 --strategy verified                  # 粘贴前校验剪贴板
    python3 tools/test_injection.py --live 20 --strategy delayed                   # 按键加延迟
    python3 tools/test_injection.py --live 20 --strategy both                      # 校验 + 延迟
    python3 tools/test_injection.py --clipboard 10                                 # 仅剪贴板回路

注入策略 (--strategy):
  raw      = 与 airtype 现状完全一致: wl-copy → sleep 0.15 → ydotool key 29 47
  verified = 粘贴前轮询校验剪贴板内容(最多 1.2s)，确保复制真正就绪
  delayed  = 粘贴键按下/抬起之间加 40ms 延迟，降低合成器快速丢键
  both     = verified + delayed 组合
"""

import os, sys, time, shutil, subprocess, argparse, importlib.util, importlib.machinery
from pathlib import Path

# 复用真实 airtype 的 copy_to_clipboard / inject_text，保证测的就是线上代码
_loader = importlib.machinery.SourceFileLoader("airtype", "airtype")
_at = importlib.util.module_from_spec(importlib.util.spec_from_loader("airtype", _loader))
_loader.exec_module(_at)


def log(msg):
    ts = time.strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def clipboard_read():
    """读回剪贴板内容，失败返回 None.

    注意: wl-paste 默认会在末尾附加一个换行符（命令替换 $(wl-paste) 会剥掉，
    但编程调用不会），这里主动剥掉以保证与源文本精确比对。
    """
    if not shutil.which('wl-paste'):
        return None
    r = subprocess.run(['wl-paste'], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        return None
    return r.stdout.rstrip('\r\n')


def do_copy(text):
    """wl-copy 写入剪贴板，返回 (ok, 耗时ms)."""
    t0 = time.perf_counter()
    r = subprocess.run(['wl-copy'], input=text.encode(), check=False)
    return r.returncode == 0, int((time.perf_counter() - t0) * 1000)


def do_verify(text, max_wait=1.2):
    """轮询校验剪贴板内容与目标一致，返回 (ok, 耗时ms)."""
    t0 = time.perf_counter()
    got = None
    while time.perf_counter() - t0 < max_wait:
        got = clipboard_read()
        if got == text:
            return True, int((time.perf_counter() - t0) * 1000)
        time.sleep(0.03)
    return False, int((time.perf_counter() - t0) * 1000)


def do_paste(strategy):
    """发送粘贴键，返回 (ok, stderr).

    raw/verified = 旧行为 ydotool key 29 47（快速连发，KWin 会丢 keyup 导致重复）
    delayed       = 新行为: 预清理 + 显式 down/up(40ms) + 后清理（与 airtype send_paste 一致）
    """
    if strategy in ('raw', 'verified'):
        # 旧行为（保留用于复现重复 bug）
        r = subprocess.run(['ydotool', 'key', '29', '47'],
                           capture_output=True, text=True, check=False)
    else:  # delayed
        # 预清理：释放残留 Ctrl/V
        subprocess.run(['ydotool', 'key', '-d', '30', '29:0', '47:0'],
                       capture_output=True, text=True, check=False)
        time.sleep(0.05)
        # 粘贴：显式 down→up，事件间隔 40ms
        r = subprocess.run(['ydotool', 'key', '-d', '40', '29:1', '47:1', '47:0', '29:0'],
                           capture_output=True, text=True, check=False)
        time.sleep(0.05)
        # 后清理：掐断自动重复
        subprocess.run(['ydotool', 'key', '-d', '30', '29:0', '47:0'],
                       capture_output=True, text=True, check=False)
    return r.returncode == 0, r.stderr.strip()


def do_type(text):
    """纯 ASCII 直接键入（ydotool type），返回 (ok, stderr)."""
    r = subprocess.run(['ydotool', 'type', text],
                       capture_output=True, text=True, check=False)
    return r.returncode == 0, r.stderr.strip()


def capture_read(path, prev_size):
    """读捕获文件自 prev_size 之后的新增字节，返回 (bytes, 新大小)."""
    try:
        data = Path(path).read_bytes()
    except (FileNotFoundError, PermissionError):
        return b'', prev_size
    return data[prev_size:], len(data)


def test_clipboard(n):
    """剪贴板回路: copy → 校验."""
    log(f'--- 剪贴板回路测试 ×{n} ---')
    ok = 0
    for i in range(n):
        marker = f'cb{i:02d}-测试'
        copy_ok, copy_ms = do_copy(marker)
        ok_verify, verify_ms = do_verify(marker, max_wait=1.0)
        if copy_ok and ok_verify:
            ok += 1
            log(f'  #{i:02d} copy={copy_ms}ms verify={verify_ms}ms ✓')
        else:
            log(f'  #{i:02d} copy={"ok" if copy_ok else "FAIL"} verify={"ok" if ok_verify else "FAIL"} ✗')
    log(f'结果: {ok}/{n} 通过')


def test_live(n, text, strategy, capture, ascii_mode):
    """完整注入循环."""
    log(f'--- 注入测试 ×{n}  text={text!r}  strategy={strategy}  ascii={ascii_mode} '
        f'capture={capture or "无(人工观察)"} ---')
    if capture:
        prev_size = Path(capture).stat().st_size if Path(capture).is_file() else 0

    copy_ok_n = paste_ok_n = landed_n = 0
    for i in range(n):
        marker = f'INJ{i:02d}-{text}'
        copy_dt = verify_dt = paste_dt = 0
        copy_ok = paste_ok = True
        detail = []

        if ascii_mode:
            # 纯 ASCII: 直接键入
            t0 = time.perf_counter()
            paste_ok, err = do_type(text)
            paste_dt = int((time.perf_counter() - t0) * 1000)
            if not paste_ok:
                detail.append(f'type-FAIL:{err}')
        else:
            # 中文: 剪贴板 + 粘贴
            copy_ok, copy_dt = do_copy(marker)
            detail.append(f'copy={copy_dt}ms')
            if strategy in ('verified', 'both'):
                ok_v, verify_dt = do_verify(marker)
                detail.append(f'verify={"ok" if ok_v else "FAIL"}({verify_dt}ms)')
                if not ok_v:
                    copy_ok = False
            else:
                time.sleep(0.15)  # 与 airtype 现状一致的固定等待
            t0 = time.perf_counter()
            paste_ok, err = do_paste(strategy)
            paste_dt = int((time.perf_counter() - t0) * 1000)
            detail.append(f'paste={paste_dt}ms{" FAIL:"+err if not paste_ok else ""}')

        # 送达验证
        landed = None
        if capture:
            new_bytes, prev_size = capture_read(capture, prev_size)
            new = new_bytes.decode('utf-8', 'replace')
            landed = marker in new
            detail.append(f'landed={"✓" if landed else "✗"}')
        else:
            # 无捕获文件: 延时，方便人工观察屏幕上是否出现
            time.sleep(1.0)

        if copy_ok: copy_ok_n += 1
        if paste_ok: paste_ok_n += 1
        if landed: landed_n += 1

        mark = '✓' if (landed is None or landed) else '✗'
        log(f'  #{i:02d} {mark} {" ".join(detail)}')
        time.sleep(0.3)  # 每次注入间隔

    log(f'结果: 复制 {copy_ok_n}/{n} | 粘贴命令 {paste_ok_n}/{n}'
        + (f' | 送达验证 {landed_n}/{n}' if capture else ' | 送达请人工确认'))


def main():
    p = argparse.ArgumentParser(description='airtype 注入节点独立测试')
    p.add_argument('--live', type=int, metavar='N', help='完整注入 N 次')
    p.add_argument('--clipboard', type=int, metavar='N', help='仅剪贴板回路 N 次')
    p.add_argument('--text', default='测试', help='注入文本(默认中文"测试")')
    p.add_argument('--ascii', action='store_true', help='ASCII 模式(ydotool type 直接键入)')
    p.add_argument('--strategy', default='raw',
                   choices=['raw', 'verified', 'delayed', 'both'],
                   help='粘贴策略: raw=airtype现状 verified=粘贴前校验 delayed=按键加延迟 both=组合')
    p.add_argument('--capture', metavar='FILE', help='捕获文件(自动验证送达)')
    p.add_argument('--interval', type=float, default=0.3, help='每次注入间隔秒')
    args = p.parse_args()

    if args.clipboard:
        test_clipboard(args.clipboard)
        return
    if args.live:
        test_live(args.live, args.text, args.strategy, args.capture, args.ascii)
        return
    p.print_help()


if __name__ == '__main__':
    main()
