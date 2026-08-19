"""Create test datasets for verifying Dataset Inspector."""

import os
import csv
import json
import random
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_tabular_dataset(base_dir: str):
    """Create a sample tabular CSV dataset."""
    dataset_dir = os.path.join(base_dir, "sample_tabular")
    os.makedirs(dataset_dir, exist_ok=True)
    
    random.seed(42)
    
    # Generate CSV data
    rows = []
    headers = ["id", "name", "age", "salary", "department", "is_active", "score"]
    
    departments = ["Engineering", "Marketing", "Sales", "HR", "Finance"]
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    
    for i in range(500):
        row = {
            "id": i + 1,
            "name": random.choice(names),
            "age": random.randint(22, 65) if random.random() > 0.02 else None,
            "salary": round(random.gauss(75000, 20000), 2) if random.random() > 0.05 else None,
            "department": random.choice(departments),
            "is_active": random.choice([True, False]),
            "score": round(random.gauss(50, 15), 1),
        }
        
        # Add some outliers
        if random.random() < 0.03:
            row["salary"] = round(random.uniform(200000, 500000), 2)
        if random.random() < 0.02:
            row["score"] = round(random.uniform(95, 100), 1)
        
        rows.append(row)
    
    # Add some duplicates
    for _ in range(10):
        rows.append(rows[random.randint(0, 100)].copy())
    
    # Write CSV
    filepath = os.path.join(dataset_dir, "employees.csv")
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    
    print(f"Created tabular dataset: {filepath} ({len(rows)} rows)")
    return dataset_dir


def create_image_dataset(base_dir: str):
    """Create a sample image classification dataset."""
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not available, skipping image dataset")
        return None
    
    dataset_dir = os.path.join(base_dir, "sample_images")
    
    random.seed(42)
    
    classes = {"cats": 30, "dogs": 25, "birds": 8}
    splits = {"train": 0.7, "test": 0.3}
    
    for split_name, split_ratio in splits.items():
        for class_name, total_count in classes.items():
            count = max(1, int(total_count * split_ratio))
            class_dir = os.path.join(dataset_dir, split_name, class_name)
            os.makedirs(class_dir, exist_ok=True)
            
            for i in range(count):
                # Create random colored images of varying sizes
                w = random.choice([64, 128, 256, 512])
                h = random.choice([64, 128, 256, 512])
                
                # Different color ranges per class
                if class_name == "cats":
                    color = (random.randint(150, 255), random.randint(100, 200), random.randint(50, 150))
                elif class_name == "dogs":
                    color = (random.randint(100, 200), random.randint(80, 180), random.randint(50, 120))
                else:
                    color = (random.randint(50, 150), random.randint(100, 200), random.randint(150, 255))
                
                img = Image.new("RGB", (w, h), color)
                
                # Add some noise
                pixels = img.load()
                for x in range(0, w, 4):
                    for y in range(0, h, 4):
                        noise = random.randint(-30, 30)
                        r = max(0, min(255, color[0] + noise))
                        g = max(0, min(255, color[1] + noise))
                        b = max(0, min(255, color[2] + noise))
                        pixels[x, y] = (r, g, b)
                
                # Random brightness
                if random.random() < 0.1:
                    # Very dark image
                    img = Image.new("RGB", (w, h), (10, 10, 10))
                
                fmt = random.choice(["JPEG", "PNG"]) if random.random() > 0.8 else "JPEG"
                ext = ".jpg" if fmt == "JPEG" else ".png"
                filepath = os.path.join(class_dir, f"{class_name}_{split_name}_{i:04d}{ext}")
                img.save(filepath, format=fmt)
    
    # Create a duplicate
    import shutil
    src = os.path.join(dataset_dir, "train", "cats")
    files = os.listdir(src)
    if len(files) >= 2:
        shutil.copy(
            os.path.join(src, files[0]),
            os.path.join(src, f"duplicate_{files[0]}")
        )
    
    # Create a corrupted file
    corrupted_path = os.path.join(dataset_dir, "train", "cats", "corrupted.jpg")
    with open(corrupted_path, "wb") as f:
        f.write(b"not a real image")
    
    total = sum(
        len(os.listdir(os.path.join(dataset_dir, s, c)))
        for s in splits
        for c in classes
        if os.path.exists(os.path.join(dataset_dir, s, c))
    )
    print(f"Created image dataset: {dataset_dir} ({total} files)")
    return dataset_dir


if __name__ == "__main__":
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
    os.makedirs(test_dir, exist_ok=True)
    
    tabular_path = create_tabular_dataset(test_dir)
    image_path = create_image_dataset(test_dir)
    
    print("\n--- Running analysis on tabular dataset ---")
    from backend.reports.engine import run_analysis
    
    report = run_analysis(tabular_path, progress_callback=lambda u: print(f"  [{u.stage}] {u.message}"))
    
    print(f"\n  Health: {report.health.score:.0f}/100 (Grade {report.health.grade})")
    print(f"  Findings: {sum(len(r.findings) for r in report.analyzer_results)}")
    print(f"  Analyzers: {len(report.analyzer_results)}")
    print(f"  Duration: {report.analysis_duration_seconds:.2f}s")
    
    if image_path:
        print("\n--- Running analysis on image dataset ---")
        report2 = run_analysis(image_path, progress_callback=lambda u: print(f"  [{u.stage}] {u.message}"))
        
        print(f"\n  Health: {report2.health.score:.0f}/100 (Grade {report2.health.grade})")
        print(f"  Findings: {sum(len(r.findings) for r in report2.analyzer_results)}")
        print(f"  Analyzers: {len(report2.analyzer_results)}")
        print(f"  Duration: {report2.analysis_duration_seconds:.2f}s")
    
    print("\n✓ All tests passed!")
