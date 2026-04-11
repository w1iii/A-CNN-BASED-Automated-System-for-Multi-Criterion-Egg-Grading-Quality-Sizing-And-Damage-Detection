import os

labels_dir = "/Users/wii/Projects/python/egg-cv/data/eggs/labels"

for split in ["train", "val", "test"]:
    split_dir = os.path.join(labels_dir, split)
    if not os.path.exists(split_dir):
        continue
    
    for filename in os.listdir(split_dir):
        if not filename.endswith(".txt"):
            continue
        
        filepath = os.path.join(split_dir, filename)
        
        with open(filepath, "r") as f:
            lines = f.readlines()
        
        if filename.startswith("damaged_"):
            new_lines = []
            for line in lines:
                parts = line.strip().split()
                if parts:
                    parts[0] = "1"
                    new_lines.append(" ".join(parts) + "\n")
            with open(filepath, "w") as f:
                f.writelines(new_lines)
            print(f"Updated (damaged=1): {filename}")
        
        elif filename.startswith("not_damaged_"):
            new_lines = []
            for line in lines:
                parts = line.strip().split()
                if parts:
                    parts[0] = "0"
                    new_lines.append(" ".join(parts) + "\n")
            with open(filepath, "w") as f:
                f.writelines(new_lines)
            print(f"Updated (not_damaged=0): {filename}")

print("\nAll annotation files updated successfully!")
