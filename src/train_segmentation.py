"""
MONAI-based 3D U-Net training for sinus segmentation.

Trains a 3D U-Net on synthetic + real sinus CT data to segment:
- Air cavities
- Mucosal thickening
- Fluid levels
- Opacified sinuses
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
from monai.data import CacheDataset, DataLoader, decollate_batch
from monai.inferers import sliding_window_inference
from monai.losses import DiceCELoss
from monai.metrics import DiceMetric
from monai.networks.nets import UNet
from monai.transforms import (
    AsDiscreted,
    Compose,
    EnsureChannelFirstd,
    LoadImaged,
    RandFlipd,
    RandRotate90d,
    RandSpatialCropd,
    ScaleIntensityRanged,
    Spacingd,
)
from monai.utils import set_determinism

logger = logging.getLogger(__name__)


class SinusSegmentationTrainer:
    """Train 3D U-Net for sinus segmentation."""
    
    def __init__(
        self,
        config_path: Path,
        device: str | None = None,
    ):
        # Load configuration
        with open(config_path) as f:
            import yaml
            self.config = yaml.safe_load(f)
        
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Initialize model
        self.model = self._build_model()
        
        # Loss and metrics
        self.loss_function = DiceCELoss(to_onehot_y=True, softmax=True)
        self.dice_metric = DiceMetric(include_background=False, reduction="mean")
        
        # Optimizer
        lr = self.config["training"]["learning_rate"]
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        # Training state
        self.best_metric = -1
        self.best_metric_epoch = -1
        
    def _build_model(self) -> torch.nn.Module:
        """Build 3D U-Net from config."""
        model_cfg = self.config["model"]
        model = UNet(
            spatial_dims=model_cfg["spatial_dims"],
            in_channels=model_cfg["in_channels"],
            out_channels=model_cfg["out_channels"],
            channels=model_cfg["channels"],
            strides=model_cfg["strides"],
        ).to(self.device)
        
        logger.info(f"Built model: {model_cfg['name']}")
        return model
    
    def _get_train_transforms(self) -> Compose:
        """Build training data augmentation pipeline."""
        return Compose([
            LoadImaged(keys=["image", "mask"]),
            EnsureChannelFirstd(keys=["image", "mask"]),
            Spacingd(
                keys=["image", "mask"],
                pixdim=[1.0, 1.0, 1.0],
                mode=["bilinear", "nearest"],
            ),
            ScaleIntensityRanged(
                keys=["image"],
                a_min=-1000,
                a_max=400,
                b_min=0.0,
                b_max=1.0,
                clip=True,
            ),
            RandSpatialCropd(
                keys=["image", "mask"],
                roi_size=self.config["training"]["patch_size"],
                random_center=True,
                random_size=False,
            ),
            RandFlipd(keys=["image", "mask"], prob=0.5, spatial_axis=0),
            RandRotate90d(keys=["image", "mask"], prob=0.5, spatial_axis=(0, 2)),
        ])
    
    def _get_val_transforms(self) -> Compose:
        """Build validation data pipeline (no augmentation)."""
        return Compose([
            LoadImaged(keys=["image", "mask"]),
            EnsureChannelFirstd(keys=["image", "mask"]),
            Spacingd(
                keys=["image", "mask"],
                pixdim=[1.0, 1.0, 1.0],
                mode=["bilinear", "nearest"],
            ),
            ScaleIntensityRanged(
                keys=["image"],
                a_min=-1000,
                a_max=400,
                b_min=0.0,
                b_max=1.0,
                clip=True,
            ),
        ])
    
    def prepare_dataloaders(
        self,
        train_files: List[Dict[str, str]],
        val_files: List[Dict[str, str]],
    ) -> Tuple[DataLoader, DataLoader]:
        """Create training and validation dataloaders."""
        train_transforms = self._get_train_transforms()
        val_transforms = self._get_val_transforms()
        
        train_ds = CacheDataset(
            data=train_files,
            transform=train_transforms,
            cache_rate=self.config["data"].get("cache_rate", 0.5),
            num_workers=4,
        )
        
        val_ds = CacheDataset(
            data=val_files,
            transform=val_transforms,
            cache_rate=1.0,
            num_workers=4,
        )
        
        train_loader = DataLoader(
            train_ds,
            batch_size=self.config["training"]["batch_size"],
            shuffle=True,
            num_workers=4,
        )
        
        val_loader = DataLoader(val_ds, batch_size=1, num_workers=4)
        
        logger.info(f"Training samples: {len(train_files)}, Validation samples: {len(val_files)}")
        return train_loader, val_loader
    
    def train_epoch(self, train_loader: DataLoader, epoch: int) -> float:
        """Train for one epoch."""
        self.model.train()
        epoch_loss = 0
        step = 0
        
        for batch_data in train_loader:
            step += 1
            inputs = batch_data["image"].to(self.device)
            labels = batch_data["mask"].to(self.device)
            
            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.loss_function(outputs, labels)
            loss.backward()
            self.optimizer.step()
            
            epoch_loss += loss.item()
            
            if step % 10 == 0:
                logger.info(f"Epoch {epoch} [{step}/{len(train_loader)}] - Loss: {loss.item():.4f}")
        
        epoch_loss /= step
        return epoch_loss
    
    def validate(self, val_loader: DataLoader) -> float:
        """Validate model and compute Dice metric."""
        self.model.eval()
        
        post_pred = Compose([AsDiscreted(argmax=True, to_onehot=2)])
        post_label = Compose([AsDiscreted(to_onehot=2)])
        
        with torch.no_grad():
            for val_data in val_loader:
                val_inputs = val_data["image"].to(self.device)
                val_labels = val_data["mask"].to(self.device)
                
                # Sliding window inference for full volume
                val_outputs = sliding_window_inference(
                    val_inputs,
                    roi_size=self.config["training"]["patch_size"],
                    sw_batch_size=4,
                    predictor=self.model,
                )
                
                val_outputs = [post_pred(i) for i in decollate_batch(val_outputs)]
                val_labels = [post_label(i) for i in decollate_batch(val_labels)]
                
                self.dice_metric(y_pred=val_outputs, y=val_labels)
        
        metric = self.dice_metric.aggregate().item()
        self.dice_metric.reset()
        
        return metric
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        save_dir: Path,
    ) -> None:
        """Full training loop."""
        max_epochs = self.config["training"]["max_epochs"]
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting training for {max_epochs} epochs...")
        
        for epoch in range(1, max_epochs + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Epoch {epoch}/{max_epochs}")
            logger.info(f"{'='*60}")
            
            # Train
            train_loss = self.train_epoch(train_loader, epoch)
            logger.info(f"Epoch {epoch} average loss: {train_loss:.4f}")
            
            # Validate every 5 epochs
            if epoch % 5 == 0:
                metric = self.validate(val_loader)
                logger.info(f"Validation Dice: {metric:.4f}")
                
                # Save best model
                if metric > self.best_metric:
                    self.best_metric = metric
                    self.best_metric_epoch = epoch
                    
                    checkpoint = {
                        "epoch": epoch,
                        "state_dict": self.model.state_dict(),
                        "optimizer": self.optimizer.state_dict(),
                        "best_metric": self.best_metric,
                    }
                    
                    torch.save(checkpoint, save_dir / "best_model.pth")
                    logger.info(f"Saved new best model (Dice: {metric:.4f})")
            
            # Save checkpoint every 20 epochs
            if epoch % 20 == 0:
                checkpoint = {
                    "epoch": epoch,
                    "state_dict": self.model.state_dict(),
                    "optimizer": self.optimizer.state_dict(),
                }
                torch.save(checkpoint, save_dir / f"checkpoint_epoch_{epoch}.pth")
        
        logger.info(f"\nTraining complete!")
        logger.info(f"Best metric: {self.best_metric:.4f} at epoch {self.best_metric_epoch}")


def prepare_file_lists(
    data_dir: Path,
    train_split: float = 0.8,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Prepare training/validation file lists from data directory.
    
    Expects structure:
        data_dir/
            images/
                sample_001.nii.gz
                sample_002.nii.gz
            masks/
                sample_001.nii.gz
                sample_002.nii.gz
    """
    image_dir = data_dir / "images"
    mask_dir = data_dir / "masks"
    
    image_files = sorted(image_dir.glob("*.nii.gz"))
    
    data_dicts = []
    for img_path in image_files:
        mask_path = mask_dir / img_path.name
        if mask_path.exists():
            data_dicts.append({
                "image": str(img_path),
                "mask": str(mask_path),
            })
    
    # Split into train/val
    n_train = int(len(data_dicts) * train_split)
    train_files = data_dicts[:n_train]
    val_files = data_dicts[n_train:]
    
    return train_files, val_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train MONAI 3D U-Net for sinus segmentation")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/monai_unet_config.yaml"),
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to training data directory (with images/ and masks/ subdirs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/training_runs"),
        help="Directory to save model checkpoints",
    )
    parser.add_argument("--train-split", type=float, default=0.8, help="Training data split ratio")
    parser.add_argument("--device", choices=["cpu", "cuda"], help="Device override")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    # Set deterministic training
    set_determinism(seed=args.seed)
    
    # Prepare data
    train_files, val_files = prepare_file_lists(args.data_dir, args.train_split)
    
    if len(train_files) == 0:
        raise ValueError(f"No training data found in {args.data_dir}")
    
    # Initialize trainer
    trainer = SinusSegmentationTrainer(args.config, device=args.device)
    
    # Prepare dataloaders
    train_loader, val_loader = trainer.prepare_dataloaders(train_files, val_files)
    
    # Train
    trainer.train(train_loader, val_loader, args.output_dir)


if __name__ == "__main__":
    main()
