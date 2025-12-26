import sys
import bcrypt

db_name = sys.argv[1]
user = sys.argv[2]
password = sys.argv[3]
root_password = sys.argv[4]

# print(f'db_name {db_name}, user {user}, password {password}, root_password {root_password}')
# 用 bcrypt 加密供 users 表使用
hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

sql = f"""
CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `{db_name}`;

CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(255) PRIMARY KEY,
    hashed_password VARCHAR(255) NOT NULL
);

INSERT INTO users (username, hashed_password)
VALUES ('{user}', '{hashed}')
ON DUPLICATE KEY UPDATE hashed_password = VALUES(hashed_password);

-- 给 root 授权远程访问
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '{root_password}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

FLUSH PRIVILEGES;
"""

with open("./.init_db.sql", "w") as f:
    f.write(sql)
