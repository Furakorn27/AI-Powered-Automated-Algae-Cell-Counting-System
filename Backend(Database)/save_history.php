<?php
header('Content-Type: application/json');

$servername = "localhost";
$username   = "g6weds_algae_analysis_db";
$password   = "rqVYcmhfw6vTFSauaV8T";
$dbname     = "g6weds_algae_analysis_db";

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    echo json_encode(['status' => 'error', 'message' => 'Connection failed: ' . $conn->connect_error]);
    exit();
}

$json_data = file_get_contents('php://input');
$data = json_decode($json_data);

if (json_last_error() !== JSON_ERROR_NONE || !$data) {
    echo json_encode(['status' => 'error', 'message' => 'No data received or invalid JSON format.']);
    exit();
}

$total_cells = ($data->total_cells !== 'N/A') ? $data->total_cells : null;
$density_cells_ml = ($data->density_cells_ml !== 'N/A') ? $data->density_cells_ml : null;

$date = new DateTime($data->timestamp);
$mysql_timestamp = $date->format('Y-m-d H:i:s');

$sql = "INSERT INTO history (total_cells, density_cells_ml, file_name, analysis_date) VALUES (?, ?, ?, ?)";
$stmt = $conn->prepare($sql);

if ($stmt === false) {
    echo json_encode(['status' => 'error', 'message' => 'Failed to prepare statement: ' . $conn->error]);
    exit();
}

$stmt->bind_param(
    "idss",
    $total_cells,
    $density_cells_ml,
    $data->file_name,
    $mysql_timestamp 
);

if ($stmt->execute()) {
    echo json_encode(['status' => 'success', 'message' => 'New history record created successfully.']);
} else {
    echo json_encode(['status' => 'error', 'message' => 'Execute failed: ' . $stmt->error]);
}

$stmt->close();
$conn->close();

?>


