from PIL import Image
import numpy as np
import torch
from transformers import CLIPModel, CLIPProcessor
from .base_analyzer import BaseAnalyzer

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

class ImageAnalyzer(BaseAnalyzer):
    def eda(self, file_path: str) -> dict:
        img = Image.open(file_path).convert("RGB")
        arr = np.array(img)

        mean_rgb = arr.mean(axis=(0, 1)).tolist()

        # histogram
        hist_r, _ = np.histogram(arr[:,:,0], bins=32, range=(0,255))
        hist_g, _ = np.histogram(arr[:,:,1], bins=32, range=(0,255))
        hist_b, _ = np.histogram(arr[:,:,2], bins=32, range=(0,255))

        return {
            "width": img.width,
            "height": img.height,
            "mean_rgb": mean_rgb,
            "hist_r": hist_r.tolist(),
            "hist_g": hist_g.tolist(),
            "hist_b": hist_b.tolist(),
        }

    def drift(self, base_path: str, target_path: str) -> dict:
        def embed_image(path):
            img = Image.open(path).convert("RGB")
            inputs = clip_proc(images=img, return_tensors="pt")
            with torch.no_grad():
                emb = clip_model.get_image_features(**inputs)
            return emb / emb.norm()

        base_emb = embed_image(base_path)
        target_emb = embed_image(target_path)

        cosine = torch.nn.functional.cosine_similarity(base_emb, target_emb)
        drift_score = float(1 - cosine.item())

        return {
            "overall": drift_score,
            "method": "CLIP embedding cosine drift"
        }