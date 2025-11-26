find . -name '.ipynb_checkpoints' -type d -exec rm -rf {} +
find . -name '__pycache__' -type d -exec rm -rf {} +
find . -name '.DS_Store' -type f -exec rm -rf {} +
