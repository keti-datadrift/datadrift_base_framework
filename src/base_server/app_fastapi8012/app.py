from fastapi import FastAPI

# FastAPI 앱 생성
app = FastAPI()

# 간단한 경로 정의
@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

# /greet 경로에서 name이라는 쿼리 파라미터를 받는 엔드포인트
@app.get("/greet/")
def greet(name: str = "World"):
    return {"message": f"Hello, {name}!"}

if __name__ == "__main__":
    import uvicorn
    # 0.0.0.0 주소와 포트 8012에서 앱 실행
    uvicorn.run(app, host="0.0.0.0", port=8012)
