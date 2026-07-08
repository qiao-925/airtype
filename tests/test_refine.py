#!/usr/bin/env python3
"""
后处理模型功能测试：输入文本 → 调用 llama-cli → 校验输出 + 性能监控。

用法：
  python3 tests/test_refine.py                    # 运行全部测试
  python3 tests/test_refine.py --verbose           # 显示详细输出
  python3 tests/test_refine.py --test 1            # 只运行第 1 个测试
"""

import os, sys, time, subprocess, argparse
from pathlib import Path

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ========== 测试用例定义 ==========
# 每个用例：(输入文本, 期望包含的关键字, 描述)
# 期望关键字为空则只检查非空输出
TEST_CASES = [
    (
        "嗯那个我们明天下午三点开会吧然后你记得带那个笔记本",
        "明天",
        "去填充词：应去除 '嗯'、'那个'、'然后'，保留核心语义",
    ),
    (
        "今天今天天气不错不错",
        "天气",
        "去重复：应去除重复词句",
    ),
    (
        "明天不对后天下午开会",
        "后天",
        "自我纠正：'明天，不对，后天' 应只保留 '后天'",
    ),
    (
        "这个方案的优缺点分别是什么呢",
        "？",
        "补标点：疑问句应补全问号",
    ),
    (
        "第一步打开设置第二步点击关于第三步查看版本号",
        "",
        "结构化：口述步骤应整理为结构化文本",
    ),
    (
        "你好世界",
        "你好",
        "基本识别：简单文本应保持不变或微调",
    ),
]


def load_refine_config():
    """从 airtype 模块加载后处理配置。"""
    import importlib.machinery
    loader = importlib.machinery.SourceFileLoader("airtype", "airtype")
    spec = importlib.util.spec_from_loader("airtype", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def run_refine_test(text, prompt, model_path, llama_path, threads=4, timeout=60):
    """
    执行单次后处理推理，返回 (结果文本, 耗时秒数, stderr, returncode)。
    """
    full_prompt = f'{prompt}\n\n{text}'
    cmd = [
        str(llama_path), '-m', str(model_path), '-p', full_prompt,
        '-n', '512', '-t', str(threads),
        '--no-display-prompt', '--log-disable',
    ]

    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        return None, elapsed, 'TIMEOUT', -1
    elapsed = time.time() - t0

    raw = r.stdout.strip() if r.stdout else ''
    stderr = r.stderr.strip() if r.stderr else ''

    # 取最后一行非空输出（处理 llama-cli 的 prompt 回显）
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    result = lines[-1] if lines else ''

    return result, elapsed, stderr, r.returncode


def print_separator(char='─', width=70):
    print(char * width)


def print_test_header(index, total, description):
    print_separator()
    print(f'  测试 {index}/{total}: {description}')
    print_separator()


def main():
    parser = argparse.ArgumentParser(description='后处理模型功能测试')
    parser.add_argument('--verbose', action='store_true', help='显示详细输出')
    parser.add_argument('--test', type=int, help='只运行第 N 个测试')
    parser.add_argument('--threads', type=int, default=4, help='推理线程数')
    parser.add_argument('--timeout', type=int, default=60, help='超时秒数')
    args = parser.parse_args()

    # 加载配置
    mod = load_refine_config()
    llama_path = mod.DIR / 'llama.cpp' / 'build' / 'bin' / 'llama-cli'
    model_path = mod.DIR / 'models' / mod.REFINE_MODEL
    prompt = mod.REFINE_PROMPT

    # 前置检查
    print()
    print('═' * 70)
    print('  后处理模型功能测试')
    print('═' * 70)
    print()
    print(f'  引擎:   {llama_path}')
    print(f'  模型:   {model_path}')
    print(f'  线程:   {args.threads}')
    print(f'  超时:   {args.timeout}s')
    print(f'  用例数: {len(TEST_CASES)}')
    print()

    if not llama_path.is_file():
        print(f'  ✗ 引擎不存在: {llama_path}')
        sys.exit(1)
    if not model_path.is_file():
        print(f'  ✗ 模型不存在: {model_path}')
        sys.exit(1)
    print('  ✓ 引擎和模型就绪')
    print()

    # 预热：首次加载模型通常较慢
    print('  预热中（首次加载模型）...')
    warmup_result, warmup_time, _, _ = run_refine_test(
        '你好', prompt, model_path, llama_path, args.threads, args.timeout)
    print(f'  预热完成: {warmup_time:.1f}s')
    print()

    # 运行测试
    cases = TEST_CASES
    if args.test:
        if 1 <= args.test <= len(TEST_CASES):
            cases = [TEST_CASES[args.test - 1]]
        else:
            print(f'  ✗ 测试编号无效: {args.test}（有效范围 1-{len(TEST_CASES)}）')
            sys.exit(1)

    passed = 0
    failed = 0
    total_time = 0
    results_log = []

    for i, (text, expect_contains, description) in enumerate(cases, 1):
        if args.test:
            i = args.test

        print_test_header(i, len(TEST_CASES), description)
        print(f'  输入: "{text}"')
        print()

        result, elapsed, stderr, returncode = run_refine_test(
            text, prompt, model_path, llama_path, args.threads, args.timeout)
        total_time += elapsed

        # 性能报告
        print(f'  耗时:     {elapsed:.1f}s')
        print(f'  返回码:   {returncode}')
        if stderr and stderr != 'TIMEOUT':
            print(f'  stderr:   {stderr[:150]}')
        print()

        # 结果报告
        if result is None:
            print(f'  ✗ 输出为 None（{"超时" if stderr == "TIMEOUT" else "失败"}）')
            failed += 1
            status = 'FAIL'
        elif not result:
            print(f'  ✗ 输出为空')
            failed += 1
            status = 'FAIL'
        else:
            print(f'  输出: "{result}"')
            # 校验期望关键字
            if expect_contains:
                if expect_contains in result:
                    print(f'  ✓ 包含期望关键字: "{expect_contains}"')
                    passed += 1
                    status = 'PASS'
                else:
                    print(f'  ✗ 未包含期望关键字: "{expect_contains}"')
                    failed += 1
                    status = 'FAIL'
            else:
                print(f'  ✓ 输出非空')
                passed += 1
                status = 'PASS'

        results_log.append((i, description, status, elapsed, text, result))
        print()

    # 汇总报告
    print()
    print('═' * 70)
    print('  测试汇总')
    print('═' * 70)
    print()
    print(f'  通过:   {passed}/{passed + failed}')
    print(f'  失败:   {failed}/{passed + failed}')
    print(f'  总耗时: {total_time:.1f}s')
    if cases:
        print(f'  平均:   {total_time / len(cases):.1f}s/条')
    print()

    # 每条结果速览
    print('  详情速览:')
    print(f'  {"#":>3}  {"状态":<6} {"耗时":>6}  {"描述"}')
    print(f'  {"─"*3}  {"─"*6} {"─"*6}  {"─"*40}')
    for idx, desc, status, elapsed, inp, out in results_log:
        icon = '✓' if status == 'PASS' else '✗'
        print(f'  {idx:>3}  {icon} {status:<4} {elapsed:>5.1f}s  {desc}')

    print()

    # 性能警告
    if cases:
        avg_time = total_time / len(cases)
        if avg_time > 10:
            print(f'  ⚠ 平均耗时 {avg_time:.1f}s 较高，建议检查:')
            print(f'    - 模型大小是否合适（考虑用更小的量化）')
            print(f'    - THREADS 配置是否匹配 CPU 核心数')
            print(f'    - 是否有其他进程占用 CPU')
        elif avg_time > 5:
            print(f'  ⚠ 平均耗时 {avg_time:.1f}s，可接受但有优化空间')
        else:
            print(f'  ✓ 性能良好（平均 {avg_time:.1f}s/条）')

    print()

    # 输出对比表
    print('  输入 → 输出 对比:')
    print(f'  {"─"*66}')
    for idx, desc, status, elapsed, inp, out in results_log:
        icon = '✓' if status == 'PASS' else '✗'
        out_display = out[:50] + '...' if out and len(out) > 50 else (out or '(空)')
        inp_display = inp[:40] + '...' if len(inp) > 40 else inp
        print(f'  {icon} 输入: {inp_display}')
        print(f'    输出: {out_display}')
        print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
