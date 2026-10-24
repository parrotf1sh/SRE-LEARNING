#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量文件重命名工具
支持四种模式：序号编号、日期时间戳、字符串替换、格式转换
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("错误: 需要安装 pyyaml 库")
    print("运行: pip install pyyaml")
    sys.exit(1)


class Config:
    """配置管理类：加载 YAML 和 CLI 参数"""
    
    DEFAULT_CONFIG = {
        'directory': '.',
        'mode': 'replace',
        'pattern': '',
        'replacement': '',
        'format_options': {
            'case': 'none',
            'strip_spaces': False,
            'ext': ''
        },
        'seq_options': {
            'start': 1,
            'step': 1,
            'padding': 3,
            'prefix': 'file_'
        },
        'date_options': {
            'format': '%Y-%m-%d',
            'source': 'mtime'
        },
        'recursive': False,
        'include_pattern': '*',
        'exclude_pattern': '',
        'dry_run': True,
        'conflict_strategy': 'suffix',
        'log_file': 'rename.log',
        'enable_rollback': True
    }
    
    def __init__(self, yaml_path: Optional[str] = None, cli_args: Optional[argparse.Namespace] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        
        if yaml_path and Path(yaml_path).exists():
            self._load_yaml(yaml_path)
        
        if cli_args:
            self._apply_cli_args(cli_args)
    
    def _load_yaml(self, yaml_path: str):
        """加载 YAML 配置文件"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
        
        if yaml_config:
            for key, value in yaml_config.items():
                if key in self.config:
                    if isinstance(self.config[key], dict) and isinstance(value, dict):
                        self.config[key].update(value)
                    else:
                        self.config[key] = value
    
    def _apply_cli_args(self, args: argparse.Namespace):
        """应用 CLI 参数（优先级高于 YAML）"""
        arg_dict = vars(args)
        
        for key, value in arg_dict.items():
            if value is not None:
                # 处理下划线和连字符的转换
                config_key = key.replace('_', '-')
                if config_key in self.config or key in self.config:
                    actual_key = config_key if config_key in self.config else key
                    
                    # 处理布尔类型的字符串转换
                    if isinstance(value, str) and value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    
                    self.config[actual_key] = value
                elif key == 'config':
                    continue
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)


class Logger:
    """日志记录类"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.entries = []
    
    def log(self, old_name: str, new_name: str, status: str, message: str = ''):
        """记录一条日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = {
            'timestamp': timestamp,
            'old_name': old_name,
            'new_name': new_name,
            'status': status,
            'message': message
        }
        self.entries.append(entry)
    
    def save(self):
        """保存日志到文件"""
        if not self.entries:
            return
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"操作时间: {self.entries[0]['timestamp']}\n")
            f.write(f"{'='*80}\n")
            
            for entry in self.entries:
                f.write(f"[{entry['timestamp']}] {entry['status']}: ")
                f.write(f"{entry['old_name']} -> {entry['new_name']}")
                if entry['message']:
                    f.write(f" ({entry['message']})")
                f.write("\n")
        
        print(f"\n日志已保存到: {self.log_file}")


class Rollback:
    """回滚功能类"""
    
    @staticmethod
    def rollback(log_file: str, dry_run: bool = True):
        """从日志文件回滚操作"""
        if not Path(log_file).exists():
            print(f"错误: 日志文件 {log_file} 不存在")
            return
        
        operations = []
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析日志文件
        pattern = r'\[(.*?)\] (SUCCESS|SKIPPED|ERROR): (.*?) -> (.*?)(?:\s+\((.*?)\))?(?=\n|\Z)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            timestamp, status, old_name, new_name, message = match
            if status == 'SUCCESS':
                operations.append((new_name.strip(), old_name.strip()))
        
        if not operations:
            print("没有找到可回滚的操作")
            return
        
        print(f"找到 {len(operations)} 个操作需要回滚")
        
        if dry_run:
            print("\n预览模式（不会实际执行）：")
            for new_name, old_name in reversed(operations):
                print(f"  {new_name} -> {old_name}")
            print(f"\n如需执行回滚，请运行: python {sys.argv[0]} --rollback {log_file} --dry-run false")
        else:
            print("\n开始回滚...")
            success_count = 0
            for new_name, old_name in reversed(operations):
                try:
                    new_path = Path(new_name)
                    old_path = Path(old_name)
                    
                    if new_path.exists():
                        new_path.rename(old_path)
                        print(f"  ✓ {new_name} -> {old_name}")
                        success_count += 1
                    else:
                        print(f"  ✗ {new_name} 不存在，跳过")
                except Exception as e:
                    print(f"  ✗ {new_name} -> {old_name} 失败: {e}")
            
            print(f"\n回滚完成: 成功 {success_count}/{len(operations)}")


class SafetyCheck:
    """安全检查类"""
    
    @staticmethod
    def check_conflict(new_name: str, strategy: str, existing_files: List[str]) -> Tuple[str, str]:
        """
        检查文件名冲突
        返回: (最终文件名, 状态消息)
        """
        if new_name not in existing_files:
            return new_name, ''
        
        if strategy == 'skip':
            return '', f'冲突: {new_name} 已存在，跳过'
        
        elif strategy == 'error':
            raise FileExistsError(f'冲突: {new_name} 已存在')
        
        elif strategy == 'suffix':
            base = Path(new_name)
            stem = base.stem
            suffix = base.suffix
            counter = 1
            
            while True:
                new_name_with_suffix = f"{stem}_{counter}{suffix}"
                if new_name_with_suffix not in existing_files:
                    return new_name_with_suffix, f'自动添加后缀避免冲突'
                counter += 1
        
        return new_name, ''


class Renamer:
    """重命名核心类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = Logger(config.get('log_file'))
        self.safety = SafetyCheck()
    
    def get_files(self) -> List[Path]:
        """获取要处理的文件列表"""
        directory = Path(self.config.get('directory'))
        recursive = self.config.get('recursive')
        include_pattern = self.config.get('include_pattern')
        exclude_pattern = self.config.get('exclude_pattern')
        
        if recursive:
            files = list(directory.rglob(include_pattern))
        else:
            files = list(directory.glob(include_pattern))
        
        # 过滤掉目录
        files = [f for f in files if f.is_file()]
        
        # 应用排除模式
        if exclude_pattern:
            excluded = set(directory.glob(exclude_pattern))
            if recursive:
                excluded.update(directory.rglob(exclude_pattern))
            files = [f for f in files if f not in excluded]
        
        return sorted(files)
    
    def seq_rename(self, file: Path, index: int) -> str:
        """序号编号模式"""
        seq_options = self.config.get('seq_options')
        start = seq_options.get('start', 1)
        step = seq_options.get('step', 1)
        padding = seq_options.get('padding', 3)
        prefix = seq_options.get('prefix', 'file_')
        
        seq_num = start + (index * step)
        seq_str = str(seq_num).zfill(padding)
        
        suffix = file.suffix
        return f"{prefix}{seq_str}{suffix}"
    
    def date_rename(self, file: Path) -> str:
        """日期时间戳模式"""
        date_options = self.config.get('date_options')
        date_format = date_options.get('format', '%Y-%m-%d')
        source = date_options.get('source', 'mtime')
        
        if source == 'mtime':
            timestamp = file.stat().st_mtime
            dt = datetime.fromtimestamp(timestamp)
        elif source == 'ctime':
            timestamp = file.stat().st_ctime
            dt = datetime.fromtimestamp(timestamp)
        elif source == 'name':
            # 尝试从文件名中提取日期
            date_pattern = r'(\d{4})-?(\d{2})-?(\d{2})'
            match = re.search(date_pattern, file.stem)
            if match:
                year, month, day = match.groups()
                dt = datetime(int(year), int(month), int(day))
            else:
                # 如果文件名中没有日期，使用当前时间
                dt = datetime.now()
        else:
            dt = datetime.now()
        
        date_str = dt.strftime(date_format)
        suffix = file.suffix
        original_stem = file.stem
        
        # 移除原文件名中可能的日期部分
        clean_stem = re.sub(r'\d{4}-?\d{2}-?\d{2}', '', original_stem).strip('_- ')
        
        if clean_stem:
            return f"{date_str}_{clean_stem}{suffix}"
        else:
            return f"{date_str}{suffix}"
    
    def replace_rename(self, file: Path) -> str:
        """字符串替换模式"""
        pattern = self.config.get('pattern')
        replacement = self.config.get('replacement')
        
        stem = file.stem
        suffix = file.suffix
        
        # 使用正则替换
        new_stem = re.sub(pattern, replacement, stem)
        
        return f"{new_stem}{suffix}"
    
    def format_rename(self, file: Path) -> str:
        """格式转换模式"""
        format_options = self.config.get('format_options')
        case = format_options.get('case', 'none')
        strip_spaces = format_options.get('strip_spaces', False)
        ext = format_options.get('ext', '')
        
        stem = file.stem
        suffix = ext if ext else file.suffix
        
        # 大小写转换
        if case == 'lower':
            stem = stem.lower()
        elif case == 'upper':
            stem = stem.upper()
        elif case == 'title':
            stem = stem.title()
        
        # 去除空格
        if strip_spaces:
            stem = re.sub(r'\s+', '_', stem)
        
        return f"{stem}{suffix}"
    
    def rename_file(self, file: Path, new_name: str, existing_files: List[str]) -> bool:
        """执行单个文件的重命名"""
        dry_run = self.config.get('dry_run')
        conflict_strategy = self.config.get('conflict_strategy')
        
        try:
            # 检查冲突
            final_name, conflict_msg = self.safety.check_conflict(
                new_name, conflict_strategy, existing_files
            )
            
            if not final_name:
                # 跳过
                self.logger.log(str(file), str(file.parent / new_name), 'SKIPPED', conflict_msg)
                print(f"  ⊘ {file.name} -> {new_name} ({conflict_msg})")
                return False
            
            if conflict_msg:
                print(f"  ⚠ {conflict_msg}")
            
            # 构建新文件的完整路径
            new_path = file.parent / final_name
            
            if dry_run:
                self.logger.log(str(file), str(new_path), 'DRY_RUN', '')
                print(f"  {file.name} -> {final_name}")
                return True
            else:
                file.rename(new_path)
                self.logger.log(str(file), str(new_path), 'SUCCESS', '')
                print(f"  ✓ {file.name} -> {final_name}")
                return True
        
        except Exception as e:
            self.logger.log(str(file), str(file.parent / new_name), 'ERROR', str(e))
            print(f"  ✗ {file.name} -> {new_name} (错误: {e})")
            return False
    
    def execute(self):
        """执行重命名操作"""
        mode = self.config.get('mode')
        dry_run = self.config.get('dry_run')
        
        print(f"\n批量文件重命名工具")
        print(f"{'='*60}")
        print(f"模式: {mode}")
        print(f"目录: {self.config.get('directory')}")
        print(f"预览模式: {'是' if dry_run else '否'}")
        print(f"{'='*60}\n")
        
        files = self.get_files()
        
        if not files:
            print("没有找到符合条件的文件")
            return
        
        print(f"找到 {len(files)} 个文件\n")
        
        # 获取当前目录中所有文件名（用于冲突检测）
        existing_files = [f.name for f in Path(self.config.get('directory')).iterdir() if f.is_file()]
        
        success_count = 0
        for index, file in enumerate(files):
            # 根据模式生成新文件名
            if mode == 'seq':
                new_name = self.seq_rename(file, index)
            elif mode == 'date':
                new_name = self.date_rename(file)
            elif mode == 'replace':
                new_name = self.replace_rename(file)
            elif mode == 'format':
                new_name = self.format_rename(file)
            else:
                print(f"错误: 未知的模式 {mode}")
                return
            
            # 执行重命名
            if self.rename_file(file, new_name, existing_files):
                success_count += 1
                # 更新 existing_files 列表
                if not dry_run:
                    existing_files.remove(file.name)
                    existing_files.append(new_name)
        
        print(f"\n{'='*60}")
        print(f"操作完成: 成功 {success_count}/{len(files)}")
        
        if dry_run:
            print(f"\n这是预览模式，未实际执行重命名")
            print(f"如需执行，请修改配置: dry_run: false")
            print(f"或使用 CLI: --dry-run false")
        
        # 保存日志
        if not dry_run:
            self.logger.save()


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='批量文件重命名工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用配置文件
  python rename.py --config rename_config.yaml
  
  # 使用 CLI 参数（覆盖配置文件）
  python rename.py --config rename_config.yaml --mode seq --dry-run false
  
  # 回滚操作
  python rename.py --rollback rename.log
        """
    )
    
    parser.add_argument('--config', type=str, help='YAML 配置文件路径')
    parser.add_argument('--directory', type=str, help='要处理的目录')
    parser.add_argument('--mode', type=str, choices=['seq', 'date', 'replace', 'format'],
                       help='重命名模式')
    parser.add_argument('--pattern', type=str, help='替换模式：匹配模式')
    parser.add_argument('--replacement', type=str, help='替换模式：替换字符串')
    parser.add_argument('--recursive', type=bool, help='是否递归处理子目录')
    parser.add_argument('--include-pattern', type=str, help='文件名包含模式')
    parser.add_argument('--exclude-pattern', type=str, help='文件名排除模式')
    parser.add_argument('--dry-run', type=str, help='预览模式 (true/false)')
    parser.add_argument('--conflict-strategy', type=str, choices=['skip', 'suffix', 'error'],
                       help='冲突处理策略')
    parser.add_argument('--log-file', type=str, help='日志文件路径')
    parser.add_argument('--rollback', type=str, help='从日志文件回滚操作')
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    # 处理回滚
    if args.rollback:
        dry_run = True
        if args.dry_run:
            dry_run = args.dry_run.lower() == 'true'
        Rollback.rollback(args.rollback, dry_run)
        return
    
    # 加载配置
    config = Config(args.config, args)
    
    # 验证必需参数
    if not config.get('pattern') and config.get('mode') == 'replace':
        print("错误: replace 模式需要指定 --pattern 参数")
        sys.exit(1)
    
    # 执行重命名
    renamer = Renamer(config)
    renamer.execute()


if __name__ == '__main__':
    main()
