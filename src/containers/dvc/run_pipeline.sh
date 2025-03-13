# 1️⃣ git and DVC initialization
git init
dvc init

# 2️⃣ Data management (with Git)
dvc add data/raw/data.csv
git add data/.gitignore data/raw/data.csv.dvc
git commit -m "Add raw dataset"

# 3️⃣ Run pipeline
dvc repro

# 4️⃣ Check result
cat metrics.json  # { "accuracy": 0.XX }