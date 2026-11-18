import time
import zipfile
from pathlib import Path
import streamlit as st

from core.constants import DEFAULT_ARTIFACTS_DIR


def iter_files(root: Path):
    return [p for p in root.rglob('*') if p.is_file()]


def zip_directory(dir_path: Path, zip_out: Path):
    with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in dir_path.rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(dir_path))


def render_downloads(art_dir: Path):
    files = iter_files(art_dir)
    if not files:
        st.info("아티팩트 폴더에 파일이 없습니다.")
        return
    st.write(f"총 {len(files)}개 파일")
    for p in files[:200]:
        with open(p, 'rb') as f:
            st.download_button(label=f"다운로드: {p.relative_to(art_dir)}", data=f, file_name=p.name)
    st.caption("파일이 많으면 아래 ZIP로 한 번에 다운로드")
    if st.button("ZIP 생성"):
        zip_out = art_dir.parent / f"{art_dir.name}-{int(time.time())}.zip"
        zip_directory(art_dir, zip_out)
        with open(zip_out, 'rb') as f:
            st.download_button("ZIP 다운로드", f, file_name=zip_out.name)
