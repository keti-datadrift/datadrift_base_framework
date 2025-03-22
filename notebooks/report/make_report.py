import subprocess

def export_report(input_path, output_path, output_type):
    # output_type은 'html', 'pdf' 등이 될 수 있습니다.
    command = f"pandoc {input_path} -o {output_path}.{output_type}"
    subprocess.run(command, shell=True)

import os, errno
try:
    os.makedirs('tmp')
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
        
# Markdown 파일을 HTML과 PDF로 변환
export_report('report.md', './tmp/report', 'html')
export_report('report.md', './tmp/report', 'pdf')