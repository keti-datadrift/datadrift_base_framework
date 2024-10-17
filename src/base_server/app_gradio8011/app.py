import gradio as gr

# 간단한 Gradio 앱: 텍스트를 입력하면 그대로 반환하는 함수
def greet(name):
    return f"Hello {name}!"

# Gradio 인터페이스 정의
interface = gr.Interface(fn=greet, inputs="text", outputs="text")

# Gradio 앱 실행
if __name__ == "__main__":
    interface.launch(server_name="0.0.0.0", server_port=8011)