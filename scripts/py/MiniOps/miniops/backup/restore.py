"""Database restore guide and execution helper."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RestoreGuide:
    """
    Generates step-by-step restore instructions for MySQL backup recovery.

    Supports both automatic restore (via docker exec) and manual restore
    (prints commands for the operator to run).
    """

    def __init__(self, config: dict):
        self.container = config.get("container", "task-api-mysql-master-1")
        self.password = config.get("password", "root_password")

    def generate(self, backup_file: str | None = None) -> str:
        lines = [
            "=" * 60,
            "  MiniOps - MySQL 数据库恢复指南",
            "=" * 60,
            "",
        ]

        if backup_file:
            lines.extend([
                f"备份文件: {backup_file}",
                "",
            ])

        lines.extend([
            "## 前置检查",
            "",
            "1. 确认 MySQL 容器正在运行:",
            f"   docker ps --filter name={self.container}",
            "",
            "2. 确认备份文件存在且完整:",
            f"   ls -lh {backup_file or '<备份文件路径>'}",
            "",
            "## 恢复步骤",
            "",
            "### 方式一：自动恢复（推荐）",
            "",
            "运行以下命令执行恢复:",
            f"   miniops restore --file {backup_file or '<备份文件路径>'} --execute",
            "",
            "### 方式二：手动恢复",
            "",
            "#### 步骤 1: 解压备份文件（如果是 .gz 格式）",
            "   gunzip <backup_file>.sql.gz",
            "",
            "#### 步骤 2: 停止应用容器（避免写入冲突）",
            "   docker stop task-api-task-api-1",
            "",
            "#### 步骤 3: 导入数据到 MySQL Master",
            "   # 方法 A: 通过 docker exec + stdin",
            f"   docker exec -i {self.container} mysql -uroot -p{self.password} < backup.sql",
            "",
            "   # 方法 B: 复制到容器内再导入",
            f"   docker cp backup.sql {self.container}:/tmp/backup.sql",
            f"   docker exec {self.container} mysql -uroot -p{self.password} -e 'source /tmp/backup.sql'",
            "",
            "#### 步骤 4: 验证数据完整性",
            f"   docker exec {self.container} mysql -uroot -p{self.password} -e 'SHOW DATABASES;'",
            f"   docker exec {self.container} mysql -uroot -p{self.password} -e 'USE task_api; SELECT COUNT(*) FROM tasks;'",
            "",
            "#### 步骤 5: 重建主从复制（如果从库数据不一致）",
            "   # 在 slave 容器上执行:",
            "   docker exec task-api-mysql-slave-1 mysql -uroot -p<password> -e 'STOP SLAVE;'",
            "   # 重新配置复制（参考 init-replication.sh）",
            "   docker exec task-api-mysql-slave-1 mysql -uroot -p<password> -e 'START SLAVE;'",
            "   docker exec task-api-mysql-slave-1 mysql -uroot -p<password> -e 'SHOW SLAVE STATUS\\G'",
            "",
            "#### 步骤 6: 重启应用容器",
            "   docker start task-api-task-api-1",
            "",
            "#### 步骤 7: 验证服务恢复",
            "   curl http://localhost:80/health",
            "   miniops check",
            "",
            "## 注意事项",
            "",
            "- 恢复操作会覆盖现有数据，请确认这是预期行为",
            "- 恢复前建议先做一次当前数据的备份",
            "- 如果主从数据不一致，需要重建复制关系",
            "- 恢复后检查 Redis 缓存是否需要清理:",
            "  docker exec task-api-redis-node-1-1 redis-cli -p 6379 FLUSHDB",
            "",
            "=" * 60,
        ])
        return "\n".join(lines)

    def execute_restore(self, backup_file: str) -> dict:
        """Execute restore by piping backup into MySQL container."""
        import subprocess

        path = Path(backup_file)
        if not path.exists():
            return {"success": False, "error": f"Backup file not found: {backup_file}"}

        logger.info("Restoring from %s", backup_file)

        try:
            if backup_file.endswith(".gz"):
                gunzip = subprocess.Popen(
                    ["gunzip", "-c", backup_file],
                    stdout=subprocess.PIPE,
                )
                mysql_cmd = [
                    "docker", "exec", "-i", self.container,
                    "mysql", "-uroot", f"-p{self.password}",
                ]
                proc = subprocess.run(
                    mysql_cmd,
                    stdin=gunzip.stdout,
                    capture_output=True, text=True,
                    timeout=300,
                )
                gunzip.wait()
            else:
                with open(path, "rb") as f:
                    proc = subprocess.run(
                        ["docker", "exec", "-i", self.container,
                         "mysql", "-uroot", f"-p{self.password}"],
                        stdin=f,
                        capture_output=True, text=True,
                        timeout=300,
                    )

            if proc.returncode == 0:
                logger.info("Restore completed successfully")
                return {"success": True, "message": "Restore completed"}
            return {"success": False, "error": proc.stderr.strip()}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Restore timed out after 300s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
