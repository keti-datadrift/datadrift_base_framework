# Documentation


## folder structure
```bash
./
├── source/
│   ├── conf.py
│   ├── index.rst
│   ├── setup.rst
│   ├── usage/
│   │   ├── installation.rst
│   │   ├── tutorial.rst
│   ├── api/
│       ├── module1.rst
│       ├── module2.rst
├── build/
```

## 스핑크스 테마별 특징 (gemini 답변)

API 설명을 깔끔하게 표시하는 데 유용한 스핑크스 테마는 여러 가지가 있습니다. 각각 특징이 있으며, 프로젝트의 스타일에 맞춰 선택할 수 있습니다. 몇 가지 인기 있는 테마와 적용 방법을 안내해 드립니다.

**추천 스핑크스 테마:**

1.  **Read the Docs (기본 테마):**
    * **특징:** 깔끔하고 읽기 쉬운 디자인으로, 많은 오픈 소스 프로젝트에서 사용됩니다. 좌측 사이드바를 통해 탐색이 용이하며, API 문서에 적합한 스타일을 제공합니다. 스핑크스를 설치하면 기본적으로 포함되어 있습니다.
    * **장점:** 널리 사용되어 익숙하며, 다양한 기능을 지원합니다.
    * **단점:** 디자인이 다소 기본적인 느낌을 줄 수 있습니다.

2.  **Sphinx Book Theme:**
    * **특징:** 현대적이고 반응형 디자인을 제공합니다. 책과 같은 레이아웃으로, API 레퍼런스와 함께 튜토리얼, 개념 설명 등을 포함하는 문서에 적합합니다.
    * **장점:** 세련된 디자인, 뛰어난 반응형 지원, 다양한 설정 옵션 제공.
    * **단점:** 추가 설치가 필요합니다.

3.  **Furo:**
    * **특징:** 가독성과 개발자 경험에 중점을 둔 현대적인 테마입니다. 깔끔한 타이포그래피와 명확한 구조를 제공하여 API 문서를 보기 쉽게 만들어줍니다.
    * **장점:** 매우 깔끔하고 현대적인 디자인, 뛰어난 검색 기능, 접근성 향상에 신경 쓴 테마.
    * **단점:** 비교적 새로운 테마로, 커뮤니티 지원이 다른 테마에 비해 적을 수 있습니다. 추가 설치가 필요합니다.

4.  **Pydata Sphinx Theme:**
    * **특징:** 과학 기술 문서에 특화된 테마이지만, 깔끔하고 체계적인 구조로 API 문서에도 잘 어울립니다. 탐색 바와 사이드바를 통해 정보를 효율적으로 전달합니다.
    * **장점:** 잘 구성된 레이아웃, 다양한 설정 옵션, 과학 기술 커뮤니티에서 널리 사용됨.
    * **단점:** 과학 기술 분야 외의 프로젝트에는 디자인이 다소 전문적으로 느껴질 수 있습니다. 추가 설치가 필요합니다.

**테마 적용 방법:**

대부분의 외부 테마는 `pip`를 사용하여 설치하고, `conf.py` 파일에서 `html_theme` 설정을 변경하여 적용합니다.

**1. 테마 설치 (Read the Docs 테마는 생략 가능):**

터미널에서 다음 명령어를 사용하여 원하는 테마를 설치합니다.

* **Sphinx Book Theme:**
    ```bash
    pip install sphinx-book-theme
    ```
* **Furo:**
    ```bash
    pip install furo
    ```
* **Pydata Sphinx Theme:**
    ```bash
    pip install pydata-sphinx-theme
    ```

**2. `conf.py` 파일 수정:**

`documentation` 폴더에 있는 `conf.py` 파일을 열고 `html_theme` 변수를 원하는 테마 이름으로 변경합니다.

* **Read the Docs (기본 테마):**
    ```python
    html_theme = 'sphinx_rtd_theme'  # 명시적으로 사용하고 싶을 경우
    ```

    **참고:** 스핑크스 버전에 따라 기본 테마가 Read the Docs일 수 있으며, 이 경우 별도로 설정하지 않아도 됩니다. 만약 `sphinx_rtd_theme`를 사용하고 싶다면 먼저 설치해야 합니다 (`pip install sphinx-rtd-theme`).

* **Sphinx Book Theme:**
    ```python
    html_theme = 'sphinx_book_theme'
    ```

* **Furo:**
    ```python
    html_theme = 'furo'
    ```

* **Pydata Sphinx Theme:**
    ```python
    html_theme = 'pydata_sphinx_theme'
    ```

**3. HTML 빌드:**

`Makefile` 또는 명령줄을 사용하여 HTML 문서를 다시 빌드합니다.

```bash
make html
```

또는

```bash
sphinx-build -b html documentation _build
```

빌드가 완료되면 `_build/html` 폴더에서 변경된 테마가 적용된 문서를 확인할 수 있습니다.

**추가 설정 (선택 사항):**

일부 테마는 추가적인 설정 옵션을 제공합니다. 예를 들어, Sphinx Book Theme은 로고, 탐색 메뉴 등을 사용자 정의할 수 있습니다. 각 테마의 공식 문서를 참고하여 원하는 설정을 추가할 수 있습니다.

**예시 (`conf.py` - Sphinx Book Theme 추가 설정):**

```python
html_theme = 'sphinx_book_theme'
html_logo = '_static/my_logo.png'
html_theme_options = {
    "repository_url": "https://github.com/your-repo",
    "path_to_docs": "documentation",
    "repository_branch": "main",
    "launch_buttons": {
        "binderhub_url": "https://mybinder.org",
        "colab_url": "https://colab.research.google.com",
    },
}
```

**결론:**

API 설명을 깔끔하게 표시하기 위해 **Read the Docs**, **Sphinx Book Theme**, **Furo**, **Pydata Sphinx Theme** 등의 테마를 고려해 볼 수 있습니다. 각 테마의 특징과 프로젝트의 요구 사항을 고려하여 가장 적합한 테마를 선택하고, 위에 설명된 방법으로 적용해 보세요. 필요에 따라 테마별 설정을 추가하여 더욱 맞춤화된 문서를 만들 수 있습니다.


