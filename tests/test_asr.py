"""airtype ASR 策略函数单元测试（mock 模式，不需要实际模型）."""
import os, sys, importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_module():
    """加载 airtype 模块（无扩展名文件需要指定 loader）."""
    loader = importlib.machinery.SourceFileLoader("airtype", "airtype")
    spec = importlib.util.spec_from_loader("airtype", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_run_asr_sensevoice_cmd():
    """测试 SenseVoice 引擎的命令构造."""
    mod = _load_module()
    mod.DIR = Path('/tmp/test-airtype')
    mod.ASR_ENGINE = 'sensevoice'
    mod.MODEL = 'sense-voice-small-q5_k.gguf'
    mod.LANG = 'zh'
    mod.THREADS = 4

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='你好世界', returncode=0)
        with patch.object(Path, 'is_file', return_value=True):
            result = mod.run_asr(Path('/tmp/test.wav'))

        assert mock_run.called, "subprocess.run 应被调用"
        cmd = mock_run.call_args[0][0]
        assert 'sense-voice-main' in cmd[0], f"命令应包含 sense-voice-main，实际: {cmd}"
        assert result == '你好世界'

    print('✓ SenseVoice 命令构造正确')


def test_run_asr_qwen3asr_cmd():
    """测试 Qwen3-ASR 引擎的命令构造."""
    mod = _load_module()
    mod.DIR = Path('/tmp/test-airtype')
    mod.ASR_ENGINE = 'qwen3asr'
    mod.MODEL = 'Qwen3-ASR-0.6B-Q4_K_M.gguf'
    mod.LANG = 'zh'
    mod.THREADS = 4

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='测试文本', returncode=0)
        with patch.object(Path, 'is_file', return_value=True):
            result = mod.run_asr(Path('/tmp/test.wav'))

        cmd = mock_run.call_args[0][0]
        assert 'transcribe' in cmd[0], f"命令应包含 transcribe，实际: {cmd}"
        assert result == '测试文本'

    print('✓ Qwen3-ASR 命令构造正确')


def test_run_asr_funasr_cmd():
    """测试 Fun-ASR-Nano 引擎的命令构造."""
    mod = _load_module()
    mod.DIR = Path('/tmp/test-airtype')
    mod.ASR_ENGINE = 'funasr'
    mod.MODEL = 'qwen3-0.6b-q4km.gguf'
    mod.LANG = 'zh'
    mod.THREADS = 4

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout='方言测试', returncode=0)
        with patch.object(Path, 'is_file', return_value=True):
            result = mod.run_asr(Path('/tmp/test.wav'))

        cmd = mock_run.call_args[0][0]
        assert 'llama-funasr-cli' in cmd[0], f"命令应包含 llama-funasr-cli，实际: {cmd}"
        assert '--enc' in cmd, f"命令应包含 --enc 参数"
        assert result == '方言测试'

    print('✓ Fun-ASR-Nano 命令构造正确')


def test_run_asr_unknown_engine():
    """测试未知引擎返回空字符串."""
    mod = _load_module()
    mod.DIR = Path('/tmp/test-airtype')
    mod.ASR_ENGINE = 'unknown_engine'

    result = mod.run_asr(Path('/tmp/test.wav'))
    assert result == '', f"未知引擎应返回空字符串，实际: {result}"
    print('✓ 未知引擎处理正确')


def test_run_asr_missing_binary():
    """测试引擎二进制不存在时返回空字符串."""
    mod = _load_module()
    mod.DIR = Path('/tmp/test-airtype')
    mod.ASR_ENGINE = 'sensevoice'
    mod.MODEL = 'test.gguf'

    with patch.object(Path, 'is_file', return_value=False):
        result = mod.run_asr(Path('/tmp/test.wav'))

    assert result == '', f"引擎不存在时应返回空字符串，实际: {result}"
    print('✓ 缺失引擎二进制处理正确')


if __name__ == '__main__':
    test_run_asr_sensevoice_cmd()
    test_run_asr_qwen3asr_cmd()
    test_run_asr_funasr_cmd()
    test_run_asr_unknown_engine()
    test_run_asr_missing_binary()
    print('\n所有 ASR 策略测试通过 ✓')
