<?php
define("DB_SERVER", "mariadb");
define("DB_USERNAME", "dev");
define("DB_PASSWORD", "dev");
define("DB_NAME", "dev");

# Connection
$link = mysqli_connect(DB_SERVER, DB_USERNAME, DB_PASSWORD, DB_NAME);

# Check connection
if (!$link) {
    die("Connection failed: " . mysqli_connect_error());
}
