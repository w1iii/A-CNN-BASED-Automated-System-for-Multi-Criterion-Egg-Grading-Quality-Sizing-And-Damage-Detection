import torch
from torch.utils.data import DataLoader
from model import EggGradingCNN
from dataset import EggDataset
import yaml
import os

# Utils
from utils import get_transforms, get_labels

def main():
    # Load config
    with open('config/config.yaml', 'r') as f:
        cfg = yaml.safe_load(f)

    # Load dataset labels (implement get_labels for your CSV or annotation format)
    train_labels = get_labels('data/processed/train.csv')
    val_labels = get_labels('data/processed/val.csv')

    # Datasets
    train_dataset = EggDataset(cfg['data']['processed_dir'], train_labels, transform=get_transforms(train=True, img_size=cfg['data']['img_size']))
    val_dataset = EggDataset(cfg['data']['processed_dir'], val_labels, transform=get_transforms(train=False, img_size=cfg['data']['img_size']))

    # DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=cfg['data']['batch_size'], shuffle=True, num_workers=cfg['data']['num_workers'])
    val_loader = DataLoader(val_dataset, batch_size=cfg['data']['batch_size'], shuffle=False, num_workers=cfg['data']['num_workers'])

    # Model
    model = EggGradingCNN(num_classes=cfg['model']['num_classes'])
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)

    # Optimizer and loss
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg['training']['lr'])
    criterion = torch.nn.CrossEntropyLoss()

    # Training loop skeleton
    for epoch in range(cfg['training']['epochs']):
        model.train()
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        print(f"Epoch {epoch+1}: loss = {loss.item():.4f}")
    
    # Save model
    torch.save(model.state_dict(), os.path.join('models', 'egg_grader.pth'))

if __name__ == '__main__':
    main()
