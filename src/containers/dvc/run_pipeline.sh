#------------------------------------------------------------------------------
# Data Drift Pipeline
#------------------------------------------------------------------------------

# 1️⃣ git and DVC initialization
git init
dvc init

# 2️⃣ 데이터 생성
python scripts/generate_data.py

# 3️⃣ Data management (with Git)
dvc add data/raw/data.csv
git add data/.gitignore data/raw/data.csv.dvc
git commit -m "Add raw dataset"

# 4️⃣ Run pipeline (preprocess → training → evaluation)
dvc repro

# 5️⃣ Check result
cat metrics.json  # { "accuracy": 0.XX }

#------------------------------------------------------------------------------
# End of this script
#------------------------------------------------------------------------------
