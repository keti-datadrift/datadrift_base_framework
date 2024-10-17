<?php
$accessed_ip = '192.168.1.777';
$hostname = 'dummy_server';
$temperature = 45.5;
$cpuclock = 2400.0;
$mem_total = 1024;
$mem_available = 720;
$json_str = json_encode(array("key" => "value"));

define("DB_SERVER", "mariadb");
define("DB_USERNAME", "dev");
define("DB_PASSWORD", "dev");
define("DB_NAME", "dev");

# Connection
$conn = mysqli_connect(DB_SERVER, DB_USERNAME, DB_PASSWORD, DB_NAME);

# Check connection
if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

// 데이터 삽입 쿼리
$sql = "INSERT INTO data (ip, hostname, temperature, cpuclock, mem_total, mem_available, json_str) VALUES ('{$accessed_ip}', '{$hostname}', '{$temperature}', '{$cpuclock}', '{$mem_total}', '{$mem_available}', '{$json_str}')";

// 쿼리 실행
$result = mysqli_query($conn, $sql);
echo $result;

// 접속 종료
$conn->close();
?>