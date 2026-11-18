rm -rf build dist *.egg-info __pycache__ .pytest_cache
rm -rf build/ dist/ *.egg-info

find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name "build" -exec rm -rf {} +
find . -type d -name "dist" -exec rm -rf {} +
find . -type d -name "*.egg-info" -exec rm -rf {} +
