import cv2
import numpy as np
from transformers import CLIPModel, CLIPProcessor
from .base_analyzer import BaseAnalyzer

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

class VideoAnalyzer(BaseAnalyzer):
    def eda(self, file_path: str) -> dict:
        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        duration = frames / fps if fps else 0
        keyframes = []

        # Extract 5 frames evenly
        for i in np.linspace(0, frames - 1, 5).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if ok:
                keyframes.append(frame.tolist())

        cap.release()

        return {
            "duration_sec": duration,
            "fps": fps,
            "resolution": (int(width), int(height)),
            "keyframes_sample": keyframes[:2],  # preview only two frames
        }

    def drift(self, base_path: str, target_path: str) -> dict:
        def get_video_emb(path):
            cap = cv2.VideoCapture(path)
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            sample_idx = np.linspace(0, frames - 1, 3).astype(int)
            embeddings = []

            for idx in sample_idx:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if ok:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    inputs = clip_proc(images=frame, return_tensors="pt")
                    with torch.no_grad():
                        emb = clip_model.get_image_features(**inputs)
                    embeddings.append(emb)

            cap.release()

            if not embeddings:
                return None

            emb = torch.stack(embeddings).mean(dim=0)
            return emb / emb.norm()

        base_emb = get_video_emb(base_path)
        target_emb = get_video_emb(target_path)

        if base_emb is None or target_emb is None:
            return {"overall": 0}

        cosine = torch.nn.functional.cosine_similarity(base_emb, target_emb)
        score = float(1 - cosine.item())

        return {
            "overall": score,
            "method": "video keyframe CLIP drift"
        }