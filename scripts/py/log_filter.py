#!/usr/bin/env python3
"""
日志关键字过滤器
SRE 排障工具：在日志文件中搜索关键字，显示匹配行及上下文，支持高亮和统计
"""

import os
import sys
import re
import gzip
import argparse
import time

# ============ 可配置常量 ============
CONTEXT_LINES = 3          # 默认上下文行数（前后各 N 行）
LOG_EXTENSIONS = ['.log', '.txt', '.out']  # 目录递归扫描时匹配的文件扩展名
# ====================================

# ANSI 颜色码
COLOR_RED = '\033[91m'
COLOR_GREEN = '\033[92m'
COLOR_YELLOW = '\033[93m'
COLOR_CYAN = '\033[96m'
COLOR_BOLD = '\033[1m'
COLOR_RESET = '\033[0m'
COLOR_DIM = '\033[2m'


def is_gzip_file(filepath):
    """判断是否为 gzip 压缩文件"""
    return filepath.endswith('.gz')


def open_file(filepath):
    """根据文件类型返回文件句柄（支持 gzip）"""
    if is_gzip_file(filepath):
        return gzip.open(filepath, 'rt', encoding='utf-8', errors='replace')
    return open(filepath, 'r', encoding='utf-8', errors='replace')


def compile_pattern(keywords, use_regex):
    """
    编译匹配模式，多个关键字用 OR 逻辑组合
    use_regex=True 时作为正则表达式，否则转义后作为普通字符串
    """
    if use_regex:
        pattern = '|'.join(keywords)
    else:
        pattern = '|'.join(re.escape(kw) for kw in keywords)
    return re.compile(pattern, re.IGNORECASE)


def collect_files(path):
    """
    收集目标文件列表
    - 单文件：直接返回
    - 目录：递归扫描匹配的日志文件和 gzip 文件
    """
    if os.path.isfile(path):
        return [path]

    files = []
    for root, _, filenames in os.walk(path):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            _, ext = os.path.splitext(fname)
            if ext.lower() in LOG_EXTENSIONS or is_gzip_file(fname):
                files.append(fpath)
    return sorted(files)


def format_size(size_bytes):
    """格式化文件大小为可读字符串"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def find_matches(lines, pattern, context):
    """
    查找所有匹配行及其上下文区间
    返回: (匹配行号集合, 合并后的输出区间列表)
    """
    match_line_numbers = set()
    for i, line in enumerate(lines):
        if pattern.search(line):
            match_line_numbers.add(i)

    if not match_line_numbers:
        return match_line_numbers, []

    # 构建带上下文的区间
    ranges = []
    for line_idx in match_line_numbers:
        start = max(0, line_idx - context)
        end = min(len(lines) - 1, line_idx + context)
        ranges.append((start, end))

    # 合并重叠区间
    ranges.sort()
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        if start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    return match_line_numbers, merged


def highlight_matches(line, keywords):
    """在行内高亮所有匹配的关键字（按长度降序替换，避免短串覆盖长串）"""
    sorted_kws = sorted(keywords, key=len, reverse=True)
    for kw in sorted_kws:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        line = pattern.sub(
            lambda m: f"{COLOR_RED}{COLOR_BOLD}{m.group(0)}{COLOR_RESET}",
            line
        )
    return line


def process_file(filepath, pattern, context, keywords):
    """
    处理单个文件：逐行读取、查找匹配、构建输出
    返回: (输出行列表, 文件统计信息字典)
    """
    stats = {
        'size': os.path.getsize(filepath),
        'total_lines': 0,
        'match_count': 0,
    }

    try:
        with open_file(filepath) as f:
            lines = f.readlines()
    except Exception as e:
        return [f"  [错误] 无法读取文件: {e}"], stats

    stats['total_lines'] = len(lines)

    match_lines, ranges = find_matches(lines, pattern, context)
    stats['match_count'] = len(match_lines)

    if not ranges:
        return [], stats

    output = []
    line_num_width = len(str(len(lines)))

    for range_idx, (start, end) in enumerate(ranges):
        # 匹配块之间加分隔线
        if range_idx > 0:
            output.append(f"  {COLOR_DIM}{'─' * 60}{COLOR_RESET}")

        for i in range(start, end + 1):
            line = lines[i].rstrip('\n')
            line_num = str(i + 1).rjust(line_num_width)

            if i in match_lines:
                # 匹配行：绿色行号 + 高亮内容
                highlighted = highlight_matches(line, keywords)
                output.append(
                    f"  {COLOR_GREEN}{line_num}│{COLOR_RESET} {highlighted}"
                )
            else:
                # 上下文行：暗色行号 + 普通内容
                output.append(
                    f"  {COLOR_DIM}{line_num}│{COLOR_RESET} {line}"
                )

    return output, stats


def output_results(output_lines, stats, filepath, match_count, file_header, output_file=None):
    """将单个文件的结果输出到终端或文件"""
    # 文件头始终打印到终端
    if file_header:
        print(file_header)

    if not output_lines:
        return

    text = '\n'.join(output_lines)

    if output_file:
        # 写文件时保留 ANSI 颜色码
        output_file.write(text + '\n')
        print(f"  {COLOR_CYAN}→ 已写入 {match_count} 条匹配到输出文件{COLOR_RESET}")
    else:
        print(text)


def print_summary(total_files, total_lines, total_matches, elapsed):
    """打印最终汇总统计"""
    print()
    print(f"{COLOR_BOLD}[汇总统计]{COLOR_RESET}")
    print(f"  扫描文件数: {total_files}")
    print(f"  总行数:     {total_lines}")
    print(f"  匹配行数:   {total_matches}")
    print(f"  耗时:       {elapsed:.2f}s")


def main():
    parser = argparse.ArgumentParser(
        description='日志关键字过滤器 - SRE 排障工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用示例:
  %(prog)s /var/log/app.log ERROR Timeout
  %(prog)s /var/log/app.log ERROR -c 5 -o result.txt
  %(prog)s /var/log/myapp/ ERROR -R "Error.*timeout"
  %(prog)s /var/log/myapp/ ERROR Timeout -c 5 -R -o report.txt
"""
    )
    parser.add_argument('path', help='日志文件路径或目录')
    parser.add_argument('keywords', nargs='*', help='搜索关键字（多个关键字为 OR 关系）')
    parser.add_argument('-c', '--context', type=int, default=CONTEXT_LINES,
                        help=f'上下文行数，默认 {CONTEXT_LINES}')
    parser.add_argument('-R', '--regex', action='store_true',
                        help='将关键字作为正则表达式匹配')
    parser.add_argument('-o', '--output', help='输出到文件（保留 ANSI 颜色码）')

    args = parser.parse_args()

    # 至少需要一个关键字
    if not args.keywords:
        parser.error('请至少提供一个搜索关键字')

    # 检查路径存在性
    if not os.path.exists(args.path):
        print(f"{COLOR_RED}[错误] 路径不存在: {args.path}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)

    # 编译匹配模式
    try:
        pattern = compile_pattern(args.keywords, args.regex)
    except re.error as e:
        print(f"{COLOR_RED}[错误] 正则表达式无效: {e}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)

    # 收集目标文件
    files = collect_files(args.path)
    if not files:
        print(f"{COLOR_YELLOW}[提示] 未找到可扫描的文件{COLOR_RESET}")
        sys.exit(0)

    # 打开输出文件（如需）
    out_f = None
    if args.output:
        out_f = open(args.output, 'w', encoding='utf-8')

    start_time = time.time()
    total_files = 0
    total_lines = 0
    total_matches = 0

    try:
        for filepath in files:
            total_files += 1
            output_lines, stats = process_file(
                filepath, pattern, args.context, args.keywords
            )
            total_lines += stats['total_lines']
            total_matches += stats['match_count']

            # 构建文件头信息
            file_header = (
                f"\n{COLOR_CYAN}{COLOR_BOLD}[文件]{COLOR_RESET} "
                f"{COLOR_CYAN}{filepath}{COLOR_RESET} "
                f"(大小: {format_size(stats['size'])}, "
                f"行数: {stats['total_lines']}, "
                f"匹配: {stats['match_count']})"
            )

            output_results(
                output_lines, stats, filepath,
                stats['match_count'], file_header, out_f
            )
    finally:
        if out_f:
            out_f.close()

    elapsed = time.time() - start_time
    print_summary(total_files, total_lines, total_matches, elapsed)


if __name__ == '__main__':
    main()
