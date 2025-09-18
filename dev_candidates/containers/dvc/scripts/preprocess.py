#------------------------------------------------------------------------------
# title : preprocess.py
# by : JPark @ KETI, since March 2025
# function : Split data into training and test sets and save them
#------------------------------------------------------------------------------

import pandas as pd
from sklearn.model_selection import train_test_split

# 데이터 로드
data = pd.read_csv("data/raw/data.csv")

# 데이터 분할 (80% 학습, 20% 테스트)
train, test = train_test_split(data, test_size=0.2, random_state=42)

# 저장
train.to_csv("data/processed/train.csv", index=False)
test.to_csv("data/processed/test.csv", index=False)

print("✅ Data preprocessing complete! Train and test sets saved.")

#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------
