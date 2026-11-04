"""MySQL backup via mysqldump inside Docker container."""

import gzip
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MySQLBackup:
    """
    Performs logical backup of MySQL using mysqldump inside Docker container.

    Backup strategy:
    - Full dump via `mysqldump --all-databases --single-transaction`
    - Output saved to configurable directory with timestamp
    - Optional gzip compression
    - Automatic rotation to keep only the most recent N backups
    """

    def __init__(self, config: dict):
        self.container = config.get("container", "task-api-mysql-master-1")
        self.password = config.get("password", "root_password")
        self.backup_dir = Path(config.get("backup_dir", "./backups"))
        self.compress = config.get("compress", True)
        self.retention_count = config.get("retention_days", 7)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> dict:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mysql_backup_{timestamp}.sql"
        if self.compress:
            filename += ".gz"
        filepath = self.backup_dir / filename

        logger.info("Starting MySQL backup to %s", filepath)

        try:
            dump_cmd = (
                f"mysqldump -uroot -p{self.password} "
                f"--all-databases --single-transaction --routines --triggers"
            )
            docker_cmd = ["docker", "exec", self.container] + dump_cmd.split()

            with open(filepath, "wb") as f:
                proc = subprocess.run(
                    docker_cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    timeout=300,
                )

            if proc.returncode != 0:
                stderr = proc.stderr.decode() if proc.stderr else "unknown error"
                logger.error("mysqldump failed: %s", stderr)
                filepath.unlink(missing_ok=True)
                return {"success": False, "error": stderr, "file": None}

            if self.compress:
                self._compress_file(filepath)
                filepath = filepath.with_suffix(".sql.gz")

            size_mb = filepath.stat().st_size / (1024 * 1024)
            logger.info("Backup completed: %s (%.2f MB)", filepath, size_mb)

            self._rotate_old_backups()

            return {
                "success": True,
                "file": str(filepath),
                "size_mb": round(size_mb, 2),
                "timestamp": timestamp,
            }

        except subprocess.TimeoutExpired:
            logger.error("Backup timed out after 300s")
            filepath.unlink(missing_ok=True)
            return {"success": False, "error": "timeout", "file": None}
        except Exception as e:
            logger.error("Backup failed: %s", e)
            filepath.unlink(missing_ok=True)
            return {"success": False, "error": str(e), "file": None}

    def _compress_file(self, filepath: Path):
        sql_path = filepath.with_suffix("")
        gz_path = filepath
        with open(sql_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        sql_path.unlink()

    def _rotate_old_backups(self):
        backups = sorted(
            self.backup_dir.glob("mysql_backup_*.sql*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[self.retention_count:]:
            logger.info("Rotating old backup: %s", old)
            old.unlink()

    def list_backups(self) -> list[dict]:
        backups = []
        for f in sorted(self.backup_dir.glob("mysql_backup_*"), reverse=True):
            stat = f.stat()
            backups.append({
                "file": str(f),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return backups
