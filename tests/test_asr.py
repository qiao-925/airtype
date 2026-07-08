"""airtype ASR 策略函数单元测试（mock 模式，不需要实际模型）."""
import os, sys, importlib.util, importlib.machinery
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_module():
    loader = importlib.machinery.SourceFileLoader("airtype", "airtype")
    spec = importlib.util.spec_from_loader("airtype", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_run_asr():
    """测试 run_asr 命令构造."""
    mod = _load_module()
    mod.DIR = Path('/tmp/test-airtype')
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
        assert '-m' in cmd, f"命令应包含 -m 参数"
        assert '--use-itn' in cmd, f"命令应包含 --use-itn"
        assert result == '你好世界'

    print('✓ run_asr 命令构造正确')


def test_run_asr_missing_model():
    """测试模型文件不存在时返回空."""
    mod = _load_module()
    mod.DIR = Path('/tmp/test-airtype')
    mod.MODEL = 'nonexistent.gguf'

    with patch.object(Path, 'is_file', return_value=False):
        result = mod.run_asr(Path('/tmp/test.wav'))

    assert result == '', f"模型不存在时应返回空，实际: {result}"
    print('✓ 缺失模型处理正确')


if __name__ == '__main__':
    test_run_asr()
    test_run_asr_missing_model()
    print('\n所有 ASR 测试通过 ✓')
