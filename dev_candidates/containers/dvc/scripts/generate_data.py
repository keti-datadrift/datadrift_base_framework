#------------------------------------------------------------------------------
# title : generate_data.py
# by : JPark @ KETI, since March 2025
# function : Evaluation
#------------------------------------------------------------------------------

import pandas as pd
import numpy as np

# 랜덤 데이터 생성
np.random.seed(42)

num_samples = 300
feature1 = np.random.uniform(4.5, 7.5, num_samples)  # 4.5~7.5 사이 값
feature2 = np.random.uniform(2.5, 4.5, num_samples)
feature3 = np.random.uniform(1.0, 6.0, num_samples)

# label 생성 (feature1이 6 이상이면 1, 아니면 0)
labels = (feature1 >= 6).astype(int)

# 데이터프레임 생성
df = pd.DataFrame({
    "feature1": feature1,
    "feature2": feature2,
    "feature3": feature3,
    "label": labels
})

# CSV로 저장
df.to_csv("data/raw/data.csv", index=False)

print(f"✅ Generated dataset with {num_samples} samples saved to data/raw/data.csv")

#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------
