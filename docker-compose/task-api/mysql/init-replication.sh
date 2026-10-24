#!/bin/bash

echo "Waiting for MySQL master to be ready..."
until docker exec mysql-master mysql -uroot -proot_password -e "SELECT 1" &>/dev/null; do
    echo "Waiting for mysql-master..."
    sleep 2
done
echo "MySQL master is ready"

echo "Waiting for MySQL slave to be ready..."
until docker exec mysql-slave mysql -uroot -proot_password -e "SELECT 1" &>/dev/null; do
    echo "Waiting for mysql-slave..."
    sleep 2
done
echo "MySQL slave is ready"

# 在 master 上创建复制用户（如果还没有）
echo "Creating replication user on master..."
docker exec mysql-master mysql -uroot -proot_password -e "
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';
FLUSH PRIVILEGES;
"

# 获取 master 的 binlog 位置
echo "Getting master status..."
MASTER_STATUS=$(docker exec mysql-master mysql -uroot -proot_password -e "SHOW MASTER STATUS;" -s)
MASTER_LOG_FILE=$(echo "$MASTER_STATUS" | awk '{print $1}')
MASTER_LOG_POS=$(echo "$MASTER_STATUS" | awk '{print $2}')

echo "Master log file: $MASTER_LOG_FILE, position: $MASTER_LOG_POS"

# 在 slave 上配置主从复制
echo "Configuring slave to replicate from master..."
docker exec mysql-slave mysql -uroot -proot_password -e "
CHANGE MASTER TO
    MASTER_HOST='mysql-master',
    MASTER_PORT=3306,
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_password',
    MASTER_LOG_FILE='$MASTER_LOG_FILE',
    MASTER_LOG_POS=$MASTER_LOG_POS;
START SLAVE;
"

# 检查 slave 状态
echo "Checking slave status..."
docker exec mysql-slave mysql -uroot -proot_password -e "SHOW SLAVE STATUS\G" | grep -E "(Slave_IO_Running|Slave_SQL_Running|Seconds_Behind_Master)"

echo "MySQL master-slave replication setup complete!"
