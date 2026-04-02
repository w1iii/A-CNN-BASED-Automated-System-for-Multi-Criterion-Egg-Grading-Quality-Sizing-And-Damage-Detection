import pandas as pd
import os
import numpy as np

SRC = "data/processed/train_labels.csv"
TRAIN_OUT = "data/processed/train.csv"
VAL_OUT = "data/processed/val.csv"
SPLIT_RATIO = 0.8
RANDOM_SEED = 42

def main():
    df = pd.read_csv(SRC)
    # Shuffle with reproducibility
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
    n_train = int(len(df) * SPLIT_RATIO)
    train_df = df.iloc[:n_train].copy()
    val_df = df.iloc[n_train:].copy()
    os.makedirs(os.path.dirname(TRAIN_OUT), exist_ok=True)
    train_df.to_csv(TRAIN_OUT, index=False)
    val_df.to_csv(VAL_OUT, index=False)
    # Print stats
    print(f"Train size: {len(train_df)}")
    print(f"Val size: {len(val_df)}")
    print("Label counts in train:")
    print(train_df['label'].value_counts())
    print("Label counts in val:")
    print(val_df['label'].value_counts())
    print(f"Wrote {TRAIN_OUT} and {VAL_OUT}")

if __name__ == "__main__":
    main()
