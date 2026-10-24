# 批量文件重命名工具

一个功能强大的 Python 批量文件重命名工具，支持多种重命名模式和完善的的安全机制。

## 功能特性

### 四种重命名模式

1. **序号编号模式 (seq)** - 按序号给文件编号
   - 支持自定义起始值、步长、补零位数、前缀
   - 示例：`file_001.jpg`, `file_002.jpg`

2. **日期时间戳模式 (date)** - 按日期重命名
   - 支持从文件修改时间、创建时间或文件名提取日期
   - 自定义日期格式
   - 示例：`2026-10-21_photo.jpg`

3. **字符串替换模式 (replace)** - 正则表达式替换
   - 支持正则表达式匹配和替换
   - 支持反向引用
   - 示例：`IMG_001.jpg` → `vacation_001.jpg`

4. **格式转换模式 (format)** - 文件名格式转换
   - 大小写转换（lower/upper/title）
   - 去除空格
   - 统一扩展名
   - 示例：`My Document.txt` → `my_document.txt`

### 安全机制

- **预览模式 (dry-run)** - 默认开启，先预览再执行
- **冲突检测** - 三种策略：skip（跳过）、suffix（自动加后缀）、error（报错）
- **日志记录** - 详细记录每次操作
- **回滚功能** - 从日志一键恢复原始文件名

### 灵活配置

- YAML 配置文件
- CLI 命令行参数（优先级高于配置文件）
- 支持文件过滤（include/exclude pattern）
- 支持递归处理子目录

## 安装依赖

```bash
pip install pyyaml
```

## 快速开始

### 1. 使用配置文件

```bash
python rename.py --config rename_config.yaml
```

### 2. 使用 CLI 参数

```bash
# 预览模式（默认）
python rename.py --directory ./photos --mode replace --pattern "IMG_" --replacement "vacation_"

# 实际执行
python rename.py --directory ./photos --mode seq --dry-run false

# 回滚操作
python rename.py --rollback rename.log --dry-run false
```

### 3. 混合使用

CLI 参数会覆盖配置文件中的对应项：

```bash
python rename.py --config rename_config.yaml --mode date --dry-run false
```

## 配置文件说明

参考 `rename_config.yaml` 文件中的详细注释。

### 基本配置项

```yaml
# 要处理的目录
directory: "./photos"

# 重命名模式：seq / date / replace / format
mode: "replace"

# 预览模式（建议首次使用时设为 true）
dry_run: true

# 冲突处理策略：skip / suffix / error
conflict_strategy: "suffix"
```

### 模式专用配置

**replace 模式：**
```yaml
pattern: "IMG_"
replacement: "vacation_"
```

**seq 模式：**
```yaml
seq_options:
  start: 1        # 起始值
  step: 1         # 步长
  padding: 3      # 补零位数
  prefix: "file_" # 前缀
```

**date 模式：**
```yaml
date_options:
  format: "%Y-%m-%d"  # 日期格式
  source: "mtime"     # 日期来源：mtime / ctime / name
```

**format 模式：**
```yaml
format_options:
  case: "lower"       # 大小写：lower / upper / title / none
  strip_spaces: true  # 去除空格
  ext: ".jpg"         # 统一扩展名
```

## CLI 参数

```bash
--config              YAML 配置文件路径
--directory           要处理的目录
--mode                重命名模式 (seq/date/replace/format)
--pattern             替换模式：匹配模式
--replacement         替换模式：替换字符串
--recursive           是否递归处理子目录
--include-pattern     文件名包含模式
--exclude-pattern     文件名排除模式
--dry-run             预览模式 (true/false)
--conflict-strategy   冲突处理策略 (skip/suffix/error)
--log-file            日志文件路径
--rollback            从日志文件回滚操作
```

## 使用示例

### 示例 1：批量添加序号

```bash
python rename.py --directory ./photos --mode seq --dry-run false
```

输出：
```
IMG_001.jpg -> file_001.jpg
IMG_002.jpg -> file_002.jpg
```

### 示例 2：按日期重命名

```bash
python rename.py --directory ./photos --mode date --dry-run false
```

输出：
```
IMG_001.jpg -> 2026-10-21_IMG_001.jpg
```

### 示例 3：替换文件名中的关键字

```bash
python rename.py --directory ./photos --mode replace \
  --pattern "IMG_" --replacement "vacation_" --dry-run false
```

输出：
```
IMG_001.jpg -> vacation_001.jpg
```

### 示例 4：格式转换（转小写 + 去空格）

```bash
python rename.py --directory ./documents --mode format --dry-run false
```

输出：
```
My Document.txt -> my_document.txt
```

### 示例 5：只处理特定类型的文件

```bash
python rename.py --config config.yaml --include-pattern "*.jpg"
```

### 示例 6：回滚操作

```bash
# 先预览回滚结果
python rename.py --rollback rename.log

# 确认无误后执行回滚
python rename.py --rollback rename.log --dry-run false
```

## 日志文件

操作日志保存在 `rename.log`（可配置），格式如下：

```
================================================================================
操作时间: 2026-10-21 19:31:15
================================================================================
[2026-10-21 19:31:15] SUCCESS: test_files/IMG_001.jpg -> test_files/vacation_001.jpg
[2026-10-21 19:31:15] SUCCESS: test_files/IMG_002.jpg -> test_files/vacation_002.jpg
```

## 注意事项

1. **首次使用建议开启预览模式**（`dry_run: true`），确认无误后再实际执行
2. **冲突处理策略**：
   - `skip`：跳过冲突文件
   - `suffix`：自动添加数字后缀（推荐）
   - `error`：报错终止
3. **回滚功能**依赖于日志文件，请勿手动修改日志
4. **正则表达式**：replace 模式支持 Python 正则语法

## 文件结构

```
py/
├── rename.py              # 主程序
├── rename_config.yaml     # 配置文件示例
├── README.md              # 使用说明
```

## 许可证

本工具仅供学习和个人使用。
