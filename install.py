#!/usr/bin/env python3
"""airtype 安装. curl -fsSL .../install.py | python3"""

import os, sys, shutil, subprocess, urllib.request
from pathlib import Path

APP = 'airtype'
DIR = Path.home() / '.local' / 'share' / APP
BIN = Path.home() / '.local' / 'bin'
REPO_SENSEVOICE = 'https://github.com/lovemefan/SenseVoice.cpp'
REPO_LLAMA = 'https://github.com/ggml-org/llama.cpp'
REPO_BASE = 'https://raw.githubusercontent.com/qiao-925/airtype/master'
MODEL_BASE = 'https://huggingface.co/lovemefan/sense-voice-gguf/resolve/main'
STB_URL = 'https://raw.githubusercontent.com/nothings/stb/master/stb_truetype.h'

RED = '\033[0;31m'; GREEN = '\033[0;32m'; YELLOW = '\033[1;33m'; CYAN = '\033[0;36m'; NC = '\033[0m'
info = lambda m: print(f'{GREEN}[+]{NC} {m}')
warn = lambda m: print(f'{YELLOW}[!]{NC} {m}')
err  = lambda m: (print(f'{RED}[✗]{NC} {m}'), sys.exit(1))[1]
say  = lambda m: print(f'{CYAN}[*]{NC} {m}')


def ask(prompt=''):
    """从 /dev/tty 读取用户输入（pipe 安装时也能交互）."""
    if prompt:
        sys.stderr.write(prompt)
        sys.stderr.flush()
    try:
        with open('/dev/tty') as tty:
            return tty.readline().strip()
    except (OSError, IOError):
        return input(prompt)


def run(cmd, **kw):
    kw.setdefault('check', True)
    return subprocess.run(cmd, **kw)


def download(url, dest, desc='下载'):
    """带进度条的下载."""
    say(f'{desc} ...')
    try:
        urllib.request.urlretrieve(url, dest, reporthook=_progress)
        print()
    except Exception as e:
        print()
        warn(f'下载失败: {e}')
        try:
            os.remove(dest)
        except OSError:
            pass
        return False
    return True


def _progress(count, block_size, total_size):
    if total_size <= 0:
        return
    pct = min(count * block_size * 100 / total_size, 100)
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    mb_done = min(count * block_size, total_size) / (1024 * 1024)
    mb_total = total_size / (1024 * 1024)
    print(f'\r  [{bar}] {pct:5.1f}%  {mb_done:.0f}/{mb_total:.0f} MB',
          end='', flush=True)



def banner():
    print()
    print('  █████╗ ██╗██████╗ ████████╗██╗   ██╗██████╗ ███████╗')
    print(' ██╔══██╗██║██╔══██╗╚══██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝')
    print(' ███████║██║██████╔╝   ██║    ╚████╔╝ ██████╔╝█████╗  ')
    print(' ██╔══██║██║██╔══██╗   ██║     ╚██╔╝  ██╔═══╝ ██╔══╝  ')
    print(' ██║  ██║██║██║  ██║   ██║      ██║   ██║     ███████╗')
    print(' ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝     ╚══════╝')
    print('              voice to text, anywhere')
    print()


def detect_system():
    info('检测系统环境 …')
    session = os.environ.get('XDG_SESSION_TYPE', '')
    if session == 'wayland':
        info('Wayland ✓')
    else:
        warn('非 Wayland 环境，文本注入可能需要适配')


def detect_hardware():
    info('检测硬件性能 …')
    cpu_cores = os.cpu_count() or 4
    ram_mb = 0
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if 'MemTotal' in line:
                    ram_mb = int(line.split()[1]) // 1024
                    break
    except Exception:
        ram_mb = 0
    vram_mb = 0
    if shutil.which('nvidia-smi'):
        try:
            r = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                vram_mb = int(r.stdout.strip().split()[0])
        except Exception:
            pass
    say(f' CPU: {cpu_cores} cores | RAM: {ram_mb}MB')
    if vram_mb > 0:
        say(f' GPU VRAM: {vram_mb}MB')
    if vram_mb >= 6000 or ram_mb >= 16000:
        reco = 8
    elif ram_mb >= 8000:
        reco = 5
    else:
        reco = 4
    return cpu_cores, reco


MODELS = {
    '1':  ('sense-voice-small-q3_k.gguf',  '153 MB', 'q3_k'),
    '2':  ('sense-voice-small-q4_0.gguf',  '182 MB', 'q4_0'),
    '3':  ('sense-voice-small-q4_1.gguf',  '196 MB', 'q4_1'),
    '4':  ('sense-voice-small-q4_k.gguf',  '182 MB', 'q4_k'),
    '5':  ('sense-voice-small-q5_0.gguf',  '210 MB', 'q5_0'),
    '6':  ('sense-voice-small-q5_k.gguf',  '210 MB', 'q5_k'),
    '7':  ('sense-voice-small-q6_k.gguf',  '239 MB', 'q6_k'),
    '8':  ('sense-voice-small-q8_0.gguf',  '292 MB', 'q8_0'),
    '9':  ('sense-voice-small-fp16.gguf',  '470 MB', 'fp16'),
    '10': ('sense-voice-small-fp32.gguf',  '937 MB', 'fp32'),
}

# 硬件等级 → MODELS 字典 key
RECO_KEY = {4: '2', 5: '6', 8: '8'}

REFINE_MODELS = {
    '0': (None,      '0 MB',     '跳过',   ''),
    '1': ('0.5B',    '469 MB',   '0.5B',   'Qwen2.5-0.5B'),
    '2': ('1.5B',    '1066 MB',  '1.5B',   'Qwen2.5-1.5B'),
    '3': ('3B',      '2007 MB',  '3B',     'Qwen2.5-3B'),
}

# 硬件等级 → REFINE_MODELS 字典 key
REFINE_RECO_KEY = {4: '0', 5: '1', 8: '1'}


def select_model(reco):
    print()
    print('  SenseVoice-Small 量化模型 (GGUF):')
    print()
    print('  ID  量化    大小    精度      内存占用   备注')
    print('  ──  ──────  ─────  ────────  ────────   ───────────────')
    print('  1   q3_k    153 MB  损失>3%   ~350 MB    最小，极限低配')
    print('  2   q4_0    182 MB  损失 ~2%  ~400 MB    经典低配')
    print('  3   q4_1    196 MB  损失 ~2%  ~420 MB    q4_0 变体')
    print('  4   q4_k    182 MB  损失 ~2%  ~400 MB    q4 优化版')
    print('  5   q5_0    210 MB  损失~1.5% ~500 MB    ★ 日常推荐')
    print('  6   q5_k    210 MB  损失 ~1%  ~500 MB    ★ 平衡精度/速度')
    print('  7   q6_k    239 MB  损失<0.5% ~600 MB    高精度')
    print('  8   q8_0    292 MB  损失<0.3% ~700 MB    GPU 首选')
    print('  9   fp16    470 MB  无损失    ~1 GB      GPU 大显存')
    print('  10  fp32    937 MB  无损      ~2 GB      原始权重')
    print()

    reco_key = RECO_KEY.get(reco, '2')
    rdef = MODELS[reco_key]
    choice = ask(f'  输入 ID 确认或回车使用推荐 [ID {reco_key}]: ')

    if choice == '':
        tier_model, tier_size, tier_name = rdef
    elif choice in MODELS:
        tier_model, tier_size, tier_name = MODELS[choice]
    else:
        warn(f'无效选项，使用推荐: {rdef[2]}')
        tier_model, tier_size, tier_name = rdef

    info(f'选定: {tier_name} ({tier_size})')
    return tier_model, tier_size, tier_name


def select_refine_model(reco):
    print()
    print('  Qwen2.5-Instruct 后处理模型 (可选，润色识别结果):')
    print()
    print('  ID  模型                   大小      延迟     备注')
    print('  ──  ─────────────────────  ────────  ──────  ──────────────')
    print('  0   跳过（不使用后处理）     0 MB     0s      纯 STT 输出')
    print('  1   Qwen2.5-0.5B Q4_K_M    469 MB   2-4s    ★ 推荐，轻量')
    print('  2   Qwen2.5-1.5B Q4_K_M    1066 MB  3-8s    更强纠错')
    print('  3   Qwen2.5-3B  Q4_K_M     2007 MB  6-15s   最强，较慢')
    print()

    reco_key = REFINE_RECO_KEY.get(reco, '0')
    rdef = REFINE_MODELS[reco_key]
    choice = ask(f'  输入 ID 确认或回车使用推荐 [ID {reco_key}]: ')

    if choice == '':
        refine_size, refine_size_str, refine_name, _ = rdef
    elif choice in REFINE_MODELS:
        refine_size, refine_size_str, refine_name, _ = REFINE_MODELS[choice]
    else:
        warn(f'无效选项，使用推荐: {rdef[2]}')
        refine_size, refine_size_str, refine_name, _ = rdef

    if refine_size:
        info(f'选定: {refine_name} ({refine_size_str})')
    else:
        info('跳过后处理模型')
    return refine_size, refine_size_str, refine_name


def install_deps():
    info('安装系统依赖 …')
    DEPS = 'cmake gcc g++ git sox libsdl2-dev ffmpeg wtype curl make'
    if shutil.which('apt'):
        run(['sudo', 'apt', 'update', '-qq'])
        run(['sudo', 'apt', 'install', '-y'] + DEPS.split())
    elif shutil.which('dnf'):
        run(['sudo', 'dnf', 'install', '-y'] + DEPS.split())
    elif shutil.which('pacman'):
        run(['sudo', 'pacman', '-Syu', '--noconfirm'] + DEPS.split())
    else:
        warn(f'未识别包管理器，请手动安装: {DEPS}')


def build_sensevoice(cpu_cores):
    SENSEVOICE_DIR = DIR / 'SenseVoice.cpp'
    SENSEVOICE_BIN = SENSEVOICE_DIR / 'build' / 'bin' / 'sense-voice-main'
    if SENSEVOICE_BIN.is_file():
        info('SenseVoice.cpp 已就绪')
        return
    info('克隆并编译 SenseVoice.cpp (3-10 分钟) …')
    DIR.mkdir(parents=True, exist_ok=True)
    if not SENSEVOICE_DIR.is_dir():
        run(['git', 'clone', '--depth', '1', REPO_SENSEVOICE, str(SENSEVOICE_DIR)])
        run(['git', 'submodule', 'update', '--init', '--recursive'], cwd=str(SENSEVOICE_DIR))
    build_dir = SENSEVOICE_DIR / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which('nvcc'):
        info('启用 CUDA GPU 加速')
        run(['cmake', '-DCMAKE_BUILD_TYPE=Release', '-DGGML_CUDA=ON', '..'], cwd=str(build_dir))
    else:
        run(['cmake', '-DCMAKE_BUILD_TYPE=Release', '..'], cwd=str(build_dir))
    run(['make', f'-j{cpu_cores}'], cwd=str(build_dir))
    info('SenseVoice.cpp 编译完成')


def build_llama(cpu_cores):
    LLAMA_DIR = DIR / 'llama.cpp'
    LLAMA_BIN = LLAMA_DIR / 'build' / 'bin' / 'llama-cli'
    if LLAMA_BIN.is_file():
        info('llama.cpp 已就绪')
        return
    info('克隆并编译 llama.cpp (3-10 分钟) …')
    DIR.mkdir(parents=True, exist_ok=True)
    if not LLAMA_DIR.is_dir():
        run(['git', 'clone', '--depth', '1', REPO_LLAMA, str(LLAMA_DIR)])
    build_dir = LLAMA_DIR / 'build'
    build_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which('nvcc'):
        info('启用 CUDA GPU 加速')
        run(['cmake', '-DCMAKE_BUILD_TYPE=Release', '-DGGML_CUDA=ON', '..'], cwd=str(build_dir))
    else:
        run(['cmake', '-DCMAKE_BUILD_TYPE=Release', '..'], cwd=str(build_dir))
    run(['make', f'-j{cpu_cores}'], cwd=str(build_dir))
    info('llama.cpp 编译完成')


def build_overlay():
    OVERLAY_BIN = DIR / 'voice-overlay'
    if OVERLAY_BIN.is_file():
        info('voice-overlay 已就绪')
        return
    info('构建 voice-overlay …')
    DIR.mkdir(parents=True, exist_ok=True)
    stb_path = DIR / 'stb_truetype.h'
    if not stb_path.is_file():
        if not download(STB_URL, str(stb_path), '下载 stb_truetype.h'):
            err('stb_truetype.h 下载失败')
    overlay_c = DIR / 'voice-overlay.c'
    if not overlay_c.is_file():
        if not download(f'{REPO_BASE}/voice-overlay.c', str(overlay_c), '下载 voice-overlay.c'):
            err('voice-overlay.c 下载失败')
    cflags = subprocess.run(
        ['pkg-config', '--cflags', '--libs', 'sdl2'],
        capture_output=True, text=True, check=True).stdout.strip()
    run(['gcc', '-O2', '-o', str(OVERLAY_BIN), str(overlay_c)] + cflags.split() +
        ['-I', str(DIR), '-lm'])
    OVERLAY_BIN.chmod(0o755)
    try:
        stb_path.unlink()
    except FileNotFoundError:
        pass
    info('voice-overlay 已构建')


def download_model(tier_model, tier_size, tier_name):
    MODEL_DIR = DIR / 'models'
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_file = MODEL_DIR / tier_model
    if model_file.is_file():
        info(f'模型已存在: {tier_model}')
        return tier_model, tier_size, tier_name
    info(f'下载模型 {tier_model} ({tier_size}) …')
    ok = download(f'{MODEL_BASE}/{tier_model}', str(model_file), f'下载 {tier_name}')
    if ok:
        info('模型下载完成')
        return tier_model, tier_size, tier_name
    warn('下载失败，回退到 q4_0')
    tier_model, tier_size, tier_name = MODELS['2']
    model_file = MODEL_DIR / tier_model
    if not model_file.is_file():
        ok2 = download(f'{MODEL_BASE}/{tier_model}', str(model_file), '下载 q4_0')
        if not ok2:
            err('模型下载失败，请手动下载')
    info('模型下载完成')
    return tier_model, tier_size, tier_name


def download_refine_model(refine_size, refine_size_str, refine_name):
    if not refine_size:
        return refine_size, refine_size_str, refine_name
    filename = f'qwen2.5-{refine_size.lower()}-instruct-q4_k_m.gguf'
    repo = f'Qwen/Qwen2.5-{refine_size}-Instruct-GGUF'
    MODEL_DIR = DIR / 'models'
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_file = MODEL_DIR / filename
    if model_file.is_file():
        info(f'模型已存在: {filename}')
        return refine_size, refine_size_str, refine_name
    url = f'https://huggingface.co/{repo}/resolve/main/{filename}'
    info(f'下载模型 {filename} ({refine_size_str}) …')
    ok = download(url, str(model_file), f'下载 {refine_name}')
    if not ok:
        warn('后处理模型下载失败，跳过后处理')
        return None, refine_size_str, refine_name
    info('模型下载完成')
    return refine_size, refine_size_str, refine_name


def deploy_airtype_script():
    """部署 airtype 运行时到 ~/.local/bin."""
    BIN.mkdir(parents=True, exist_ok=True)
    dst = BIN / 'airtype'

    # 本地仓库
    src = Path(__file__).resolve().parent / 'airtype'
    if src.is_file():
        shutil.copy2(str(src), str(dst))
    else:
        # curl | python3 远程安装，从 GitHub 拉取
        url = f'{REPO_BASE}/airtype'
        if not download(url, str(dst), '下载 airtype 运行时'):
            err('airtype 运行时下载失败')

    dst.chmod(0o755)
    info(f'airtype → {dst}')


def deploy_config(tier_model, refine_size=None):
    config_path = DIR / 'config'
    cfg = (
        f'# airtype 配置\n'
        f'MODEL="{tier_model}"\n'
        f'MAX_SECONDS=3600\n'
        f'LANG="zh"\n'
        f'THREADS=4\n'
    )
    if refine_size:
        filename = f'qwen2.5-{refine_size.lower()}-instruct-q4_k_m.gguf'
        cfg += (
            f'REFINE_MODEL="{filename}"\n'
            f'REFINE_THREADS=4\n'
        )
    config_path.write_text(cfg)
    info(f'配置 → {config_path}')


def check_path():
    if str(BIN) not in os.environ.get('PATH', '').split(':'):
        warn(f'请将 {BIN} 加入 PATH:')
        print(f"  echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc")


def print_done(tier_name, tier_size, refine_name=None, refine_size=None):
    print()
    print('  ======================================')
    print('   airtype 安装完成')
    print('  ======================================')
    print()
    print(f'  STT 模型:  {tier_name} ({tier_size})')
    if refine_name:
        print(f'  后处理模型: {refine_name} ({refine_size})')
    print(f'  配置:  {DIR}/config')
    print(f'  日志:  {DIR}/airtype.log')
    print(f'  使用:  桌面快捷键绑定到 airtype 命令')
    print()

# ======================================================================
# 主入口
# ======================================================================
def main():
    banner()
    detect_system()
    cpu_cores, reco = detect_hardware()
    tier_model, tier_size, tier_name = select_model(reco)
    refine_size, refine_size_str, refine_name = select_refine_model(reco)
    install_deps()
    build_sensevoice(cpu_cores)
    if refine_size:
        build_llama(cpu_cores)
    build_overlay()
    tier_model, tier_size, tier_name = download_model(tier_model, tier_size, tier_name)
    refine_size, refine_size_str, refine_name = download_refine_model(refine_size, refine_size_str, refine_name)
    deploy_airtype_script()
    deploy_config(tier_model, refine_size)
    check_path()
    print_done(tier_name, tier_size, refine_name, refine_size_str)


if __name__ == '__main__':
    main()
