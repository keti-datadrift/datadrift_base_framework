# 문제 원인 되는 빌드 잔재 제거
rm -rf build/ dist/ *.egg-info
pip install build twine
python3 -m build
python3 -m twine upload dist/*
#python -m twine upload --repository testpypi dist
#tar -xvzf dist/dd-0.1.2.tar.gz
#cat dd-0.1.2/PKG-INFO | grep License