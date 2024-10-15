-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS dev;

-- 데이터베이스 사용
USE dev;

-- 데모 사용자 생성 및 비밀번호 설정 (서비스 환경에 맞춰 수정 필요)
CREATE USER IF NOT EXISTS 'dev'@'%' IDENTIFIED BY 'dev';

-- 권한 부여
GRANT ALL PRIVILEGES ON dev.* TO 'dev'@'%';

-- 권한 적용
FLUSH PRIVILEGES;

-- 테이블 생성
CREATE TABLE IF NOT EXISTS data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    temperature FLOAT NOT NULL DEFAULT '-1',
    cpuclock VARCHAR(32) NOT NULL DEFAULT '-1',
    mem_total VARCHAR(32) NOT NULL DEFAULT '-1',
    mem_available VARCHAR(32) NOT NULL DEFAULT '-1',
    json_str TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);