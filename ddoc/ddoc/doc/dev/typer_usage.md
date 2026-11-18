# Typer 사용법

Typer에서 트리 구조의 계층적 CLI 명령어를 만드는 방법은 Typer() 인스턴스를 중첩하여 하위 커맨드를 서브앱으로 등록하는 방식입니다. 아래에 실용적인 예제 중심으로 단계별 설명합니다.

## Typer 기초

⸻

✅ 목표 구조

```bash
$ app user add --name Alice
$ app user delete --id 123
$ app project create --title "My Project"
$ app project list
```

⸻

📦 전체 예제 코드

```python
import typer

# 메인 앱
app = typer.Typer()

# 하위 앱 1: user
user_app = typer.Typer()
@user_app.command("add")
def add_user(name: str):
    typer.echo(f"✅ 사용자 추가: {name}")

@user_app.command("delete")
def delete_user(id: int):
    typer.echo(f"🗑 사용자 삭제: {id}")

# 하위 앱 2: project
project_app = typer.Typer()
@project_app.command("create")
def create_project(title: str):
    typer.echo(f"📁 프로젝트 생성: {title}")

@project_app.command("list")
def list_projects():
    typer.echo("📋 프로젝트 목록 출력")

# 서브 커맨드를 메인에 등록
app.add_typer(user_app, name="user")
app.add_typer(project_app, name="project")

if __name__ == "__main__":
    app()
```

⸻

📌 실행 예시

```bash
$ python main.py user add --name Alice
✅ 사용자 추가: Alice

$ python main.py user delete --id 123
🗑 사용자 삭제: 123

$ python main.py project create --title "My Project"
📁 프로젝트 생성: My Project

$ python main.py project list
📋 프로젝트 목록 출력
```

⸻

🧠 구조 설명

구성 요소	설명
```python
app = typer.Typer()	최상위 CLI 애플리케이션
user_app = typer.Typer()	user 하위 명령 그룹
@user_app.command()	user 하위의 실제 명령
app.add_typer(user_app, name="user")	하위 앱을 user라는 이름으로 메인 앱에 등록
```

⸻

🧩 도움말 자동 생성
```bash
$ python main.py --help
Usage: main.py [OPTIONS] COMMAND [ARGS]...

Commands:
  project
  user

$ python main.py user --help
Usage: main.py user [OPTIONS] COMMAND [ARGS]...

Commands:
  add
  delete
```

⸻

🔁 중첩의 중첩도 가능

```python
admin_app = typer.Typer()
@admin_app.command()
def stats():
    typer.echo("관리자 통계 출력")

user_app.add_typer(admin_app, name="admin")
```

```bash
$ python main.py user admin stats
```

⸻

✅ 정리: Typer 계층형 구조 꿀팁

개념	내용
서브커맨드	@sub_app.command() 데코레이터 사용
트리 구조	app.add_typer(하위앱, name="명령어") 방식
깊은 계층	Typer 인스턴스를 여러 단계 중첩 등록 가능
자동 도움말	Typer가 타입 기반으로 도와줌 (예: --help)


⸻

## Typer 기반 계층적 명령어셋

네, Typer의 기본 동작은 트리의 leaf 명령어 전체를 --help에 표시하는 방식입니다. 즉, 중첩된 커맨드 구조에서도 최종 명령어 목록 전체가 한 번에 보여지는 구조지요.

하지만 당신이 원하는 “트리 레벨별로 help 표시”, 즉:
	•	main.py --help → user, project 등 최상위 그룹만 보여주고
	•	main.py user --help → add, delete 등 user 하위만 보여주고
	•	main.py user admin --help → stats 등 더 깊은 하위만

이렇게 레벨에 따라 분리된 help 출력은 Typer가 이미 지원하고 있습니다.

⸻

✅ 핵심 포인트: Typer는 CLI depth별로 help를 분리해서 출력함

📌 예시 구조
```python
app = typer.Typer()

user_app = typer.Typer()
admin_app = typer.Typer()

@user_app.command("add")
def add_user(name: str): ...

@admin_app.command("stats")
def show_stats(): ...

user_app.add_typer(admin_app, name="admin")
app.add_typer(user_app, name="user")
```

⸻

🧪 예제 실행
```bash
$ python main.py --help

출력:

Usage: main.py [OPTIONS] COMMAND [ARGS]...

Commands:
  user

$ python main.py user --help

출력:

Usage: main.py user [OPTIONS] COMMAND [ARGS]...

Commands:
  add
  admin

$ python main.py user admin --help

출력:

Usage: main.py user admin [OPTIONS] COMMAND [ARGS]...

Commands:
  stats
```

⸻

🧠 정리

동작	설명
@app.command()	단일 명령어 등록
@app.add_typer(sub_app, name="sub")	하위 커맨드 그룹 구성
--help	해당 depth에서만 보여줌 (자동)
app()	꼭 app() 호출해야 Typer CLI 작동

Typer는 Click을 기반으로 하고 있어 명령어 계층에 따라 help 출력이 자동으로 분기됩니다. 별도 설정이 필요 없이 기본으로 의도한 대로 동작합니다.

⸻

🔒 참고: 전체 커맨드 트리를 한번에 보고 싶다면?

만약 반대로 모든 계층의 명령어를 한눈에 보고 싶다면 Typer는 기본적으로는 지원하지 않지만, 다음처럼 --help 명령을 shell 도구와 조합하여 한 번에 볼 수 있습니다.
```bash
python main.py --help
python main.py user --help
python main.py user admin --help
```
혹은 모든 help 메시지를 수동으로 수집하거나, 커스텀 도움말을 작성해야 합니다.

⸻

필요하다면:
	•	커스텀 도움말 텍스트 (help=...)
	•	공통 옵션 상속
	•	Markdown 기반 CLI 문서 자동 생성
