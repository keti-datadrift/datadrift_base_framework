import pandas as pd
from .base_analyzer import BaseAnalyzer

class TabularAnalyzer(BaseAnalyzer):
    def eda(self, file_path: str) -> dict:
        """
        가장 단순한 EDA - 추후 확장 쉬움(Evidently 등)
        """

        df = pd.read_csv(file_path)
        summary = df.describe(include="all").fillna(0).to_dict()
        missing = df.isna().mean().to_dict()
    
        return {
            "shape": df.shape,
            "missing_rate": missing,
            "summary": summary,
        }

    def drift(self, base_path: str, target_path: str) -> dict:
        """
        매우 단순한 드리프트 계산 (컬럼별 평균 차이 비교)
        향후 PSI, KS 등으로 변경 가능
        """
        results = []
        numeric_cols = df_base.select_dtypes("number").columns
    
        for col in numeric_cols:
            b = df_base[col].mean()
            t = df_target[col].mean()
            diff = abs(b - t)
    
            results.append({
                "feature": col,
                "mean_base": float(b),
                "mean_target": float(t),
                "drift_score": float(diff)
            })

        #overall = sum([r["drift_score"] for r in results]) / len(results)
        overlall = '0'
        
        return {
            "overall": overall,
            "method": "todo  drift",
        }