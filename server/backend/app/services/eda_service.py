import pandas as pd
from .analyzer.tabular_analyzer import TabularAnalyzer
from .analyzer.text_analyzer import TextAnalyzer
from .analyzer.image_analyzer import ImageAnalyzer
from .analyzer.video_analyzer import VideoAnalyzer

def select_analyzer(dtype):
    return {
        "csv": TabularAnalyzer(),
        "text": TextAnalyzer(),
        "image": ImageAnalyzer(),
        "video": VideoAnalyzer(),
    }.get(dtype, TabularAnalyzer())

def run_eda(file_path: str) -> dict:
    df = pd.read_csv(file_path)

    summary = df.describe(include="all").fillna(0).to_dict()
    missing = df.isna().mean().to_dict()

    return {
        "shape": df.shape,
        "missing_rate": missing,
        "summary": summary,
    }