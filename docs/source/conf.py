# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import os
import sys

# 프로젝트 루트 경로를 계산
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

project = 'dd_docs'
copyright = '2025, KETI'
author = 'JPark @ KETI'
release = 'document v0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# -- General configuration ---------------------------------------------------

extensions = [    
    'nbsphinx',  # jupyter notebook
    'sphinx.ext.mathjax',  # For math rendering
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Google style docstrings을 사용하는 경우 추가
    'sphinx.ext.viewcode',  # 소스 코드 링크를 제공합니다.
]


templates_path = ['_templates']

# Exclude build files and Jupyter checkpoint files from Sphinx build
exclude_patterns = ['_build', '**.ipynb_checkpoints']


language = 'ko'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'alabaster'
#html_theme = 'sphinx_rtd_theme'  # read the docs
html_theme = 'sphinx_book_theme'
#html_theme = 'furo'
#html_theme = 'pydata_sphinx_theme'


html_static_path = ['_static']

html_title = "Data Drift <br/> Management SW"


# -- Options for jupyter notebook output -------------------------------------------------
# notebook
nbsphinx_execute = 'never'  # 'never', 'auto', 'always' 중 선택


# -- Options for PDF output -------------------------------------------------
master_doc = 'index'
latex_engine = 'pdflatex'
latex_documents = [
  (master_doc, 'projectname.tex', 'Project Name Documentation',
   'Author Name', 'manual'),
]