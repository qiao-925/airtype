"""airtype 配置解析单元测试.

通过环境变量 AIRTYPE_CONFIG 注入自定义 config 路径，
避免模块缓存导致的测试干扰。
"""
import os, sys, tempfile, importlib, importlib.util, importlib.machinery
from pathlib import Path

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_module(config_path=None):
    """加载 airtype 模块。如果指定 config_path，通过环境变量注入。"""
    # 清除模块缓存，确保每次重新加载
    if 'airtype' in sys.modules:
        del sys.modules['airtype']

    if config_path:
        os.environ['AIRTYPE_CONFIG'] = str(config_path)
    else:
        os.environ.pop('AIRTYPE_CONFIG', None)

    loader = importlib.machinery.SourceFileLoader("airtype", "airtype")
    spec = importlib.util.spec_from_loader("airtype", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_load_config_defaults():
    """测试默认配置值."""
    mod = _load_module()

    assert mod.ASR_ENGINE == 'sensevoice', f"默认 ASR_ENGINE 应为 sensevoice，实际为 {mod.ASR_ENGINE}"
    assert mod.MODEL == 'sense-voice-small-q5_k.gguf'
    assert mod.LANG == 'zh'
    assert mod.THREADS == 4
    assert mod.REFINE_MODEL == ''
    assert mod.REFINE_THREADS == 4
    print('✓ 默认配置值正确')


def test_load_config_from_file():
    """测试从文件加载配置."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write('# 测试配置\n')
        f.write('ASR_ENGINE="qwen3asr"\n')
        f.write('MODEL="Qwen3-ASR-0.6B-Q4_K_M.gguf"\n')
        f.write('LANG="en"\n')
        f.write('THREADS=8\n')
        f.write('REFINE_MODEL="Qwen3.5-0.8B-Q4_K_M.gguf"\n')
        f.write('REFINE_THREADS=4\n')
        tmp_path = f.name

    try:
        mod = _load_module(config_path=tmp_path)
        # load_config() 在 main() 中调用，测试中需手动调用
        mod.load_config()

        assert mod.ASR_ENGINE == 'qwen3asr', f"ASR_ENGINE 应为 qwen3asr，实际为 {mod.ASR_ENGINE}"
        assert mod.MODEL == 'Qwen3-ASR-0.6B-Q4_K_M.gguf'
        assert mod.LANG == 'en'
        assert mod.THREADS == 8
        assert mod.REFINE_MODEL == 'Qwen3.5-0.8B-Q4_K_M.gguf'
        assert mod.REFINE_THREADS == 4
        print('✓ 文件配置加载正确')
    finally:
        os.unlink(tmp_path)


def test_invalid_asr_engine():
    """测试非法 ASR_ENGINE 值被拒绝，保留默认值."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write('ASR_ENGINE="typo_engine"\n')
        tmp_path = f.name

    try:
        mod = _load_module(config_path=tmp_path)
        mod.load_config()
        # 非法值应被拒绝，保留默认值 sensevoice
        assert mod.ASR_ENGINE == 'sensevoice', \
            f"非法 ASR_ENGINE 应保留默认值 sensevoice，实际为 {mod.ASR_ENGINE}"
        print('✓ 非法 ASR_ENGINE 校验正确')
    finally:
        os.unlink(tmp_path)


def test_parse_output():
    """测试 ASR 输出解析函数."""
    mod = _load_module()

    assert mod.parse_output('你好世界') == '你好世界'
    assert mod.parse_output('[0.0-1.5] 你好世界') == '你好世界'
    assert mod.parse_output('<|zh|>你好世界') == '你好世界'
    assert mod.parse_output('你好\n世界') == '你好 世界'
    assert mod.parse_output('') == ''

    print('✓ parse_output 函数正确')


if __name__ == '__main__':
    test_load_config_defaults()
    test_load_config_from_file()
    test_invalid_asr_engine()
    test_parse_output()
    print('\n所有配置测试通过 ✓')
