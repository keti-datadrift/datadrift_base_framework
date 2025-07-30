# paraview_hello_world.py
# ParaView Python API를 임포트
from paraview.simple import *

# 1. 시각화 객체 생성 (데이터 소스)
# 기본 구(sphere) 소스를 만듭니다.
sphere = Sphere()

# 2. 뷰(View) 생성
# 3D 렌더 뷰를 생성하거나 활성화된 뷰를 가져옵니다.
# 'viewtype' 인자를 'RenderView'로 명시적으로 지정했습니다.
renderView = GetActiveViewOrCreate(viewtype='RenderView') # 오류 발생 지점 재수정

# 3. 뷰에 데이터 표시
# 생성한 구를 뷰에 표시합니다.
sphereDisplay = Show(sphere, renderView)

# 4. 카메라 설정 (옵션: 더 보기 좋게)
# 카메라 위치와 포커스 등을 조정하여 구가 잘 보이도록 합니다.
renderView.ResetCamera() # 모든 데이터를 포함하도록 카메라를 리셋합니다.

# 5. 렌더링 (화면 업데이트)
# 뷰를 렌더링하여 변경사항을 반영합니다. (파일 저장 전에 필수)
Render()

# 6. 결과 저장
# 현재 뷰의 스크린샷을 'hello_sphere.png' 파일로 저장합니다.
# 파일 이름과 해상도를 지정할 수 있습니다.
SaveScreenshot('./tmp/hello_sphere.png', renderView, ImageResolution=[600, 600])

print("ParaView Hello World: 구 이미지가 './tmp/hello_sphere.png'로 저장되었습니다.")

# ParaView 서버 연결 종료 (스크립트가 완전히 끝나도록)
# 이것은 주피터 노트북이나 대화형 세션에서는 필요 없지만, 스크립트로 실행할 때는 좋습니다.
Disconnect()