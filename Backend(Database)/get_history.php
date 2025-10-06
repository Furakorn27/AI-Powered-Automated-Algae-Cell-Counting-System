<?php
header('Content-Type: application/json');


$servername = "localhost";
$username   = "g6weds_algae_analysis_db";
$password   = "rqVYcmhfw6vTFSauaV8T";
$dbname     = "g6weds_algae_analysis_db";

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    echo json_encode([]); 
    exit();
}

$sql = "SELECT id, analysis_date, file_name, total_cells, density_cells_ml FROM history ORDER BY id DESC";
$result = $conn->query($sql);

$history_data = [];

if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        $history_data[] = $row;
    }
}

echo json_encode($history_data);

$conn->close();

?>