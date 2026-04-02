from torchvision import transforms
import pandas as pd

# Data transforms for training/validation

def get_transforms(train=True, img_size=224):
    if train:
        return transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    else:
        return transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

def get_labels(label_csv):
    df = pd.read_csv(label_csv)
    return list(zip(df['filename'], df['label']))
