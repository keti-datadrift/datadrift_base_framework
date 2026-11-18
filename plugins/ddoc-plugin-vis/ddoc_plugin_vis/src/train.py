import argparse
import time
import os
import random
from dvclive import Live

def simulate_training(data_path, yolo_config_path, epochs, batch_size, learning_rate, yaml_config):
    """
    Simulates YOLOv8 training and records metrics using DVCLive.
    Performance is simulated differently based on the data_path for comparison.
    """
    
    # Initialize Live object (DVC tracks metrics)
    live = Live("dvclive")
    
    print("=" * 60)
    print(f"🔥 Starting Training: {os.path.basename(data_path)} dataset")
    print(f"Data Root: {data_path}, YOLO Config: {yolo_config_path}")
    print(f"Epochs: {epochs}, LR: {learning_rate}, Batch: {batch_size}, Model Config: {yaml_config}")
    print("=" * 60)

    # Performance simulation based on data_path
    if 'd2' in data_path:
        # d2 dataset simulates high performance
        base_map = 0.85
        base_loss = 0.3
    else:
        # d1 dataset simulates lower performance
        base_map = 0.65
        base_loss = 0.7

    for epoch in range(1, epochs + 1):
        # Simulate training time
        time.sleep(1) 

        # Calculate and record metrics (with random noise)
        train_loss = base_loss - (0.01 * epoch) + (random.random() * 0.05)
        val_map50 = base_map + (0.01 * epoch) + (random.random() * 0.03)
        drift_mmd = 0 + (0.01 * epoch) + (random.random() * 0.03)
        drift_js = 0 + (0.01 * epoch) + (random.random() * 0.03)
        
        # Record metrics
        live.log_metric("train/loss", round(train_loss, 5))
        live.log_metric("val/mAP50", round(val_map50, 5))
        live.log_metric("val/precision", round(val_map50 * 0.95, 5))
        live.log_metric("drift/mmd", round(drift_mmd * 0.95, 5))
        live.log_metric("drift/js", round(drift_js * 0.95, 5))
        
        # DVCLive automatically tracks steps.
        live.next_step()

        
        print(f"Epoch {epoch}/{epochs}: Loss={round(train_loss, 4)}, mAP50={round(val_map50, 4)}")

    print("\n✅ Training complete and metrics recorded.")
    
    # Simulate model file creation
    os.makedirs('models', exist_ok=True)
    with open('models/model.pt', 'w') as f:
        f.write(f"Trained model checkpoint (Dataset: {data_path}, Epochs: {epochs})")
        
    print("✅ Model file (models/model.pt) saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulated YOLOv8 Trainer")
    parser.add_argument("--data_path", type=str, required=True, help="Data root path (e.g., data/d1)")
    parser.add_argument("--yolo_config_path", type=str, required=True, help="Path to the YOLO data.yaml file")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--learning_rate", type=float, default=0.01, help="Learning rate")
    parser.add_argument("--yaml_config", type=str, default="yolo_d1.yaml", help="YOLO config file")

    args = parser.parse_args()
    
    simulate_training(
        data_path=args.data_path,
        yolo_config_path=args.yolo_config_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        yaml_config=args.yaml_config
    )
