import os
import re
from datetime import datetime

class XAIGuidelineGenerator:
    def __init__(self):
        self.guideline_data = self._load_guideline_content()
    
    def _load_guideline_content(self):
        """XAI 가이드라인 내용을 구조화된 데이터로 로드합니다."""
        return {
            'title': 'XAI Report Guideline',
            'sections': [
                {
                    'title': 'CAM 분석 결과 해석',
                    'subsections': [
                        {
                            'title': 'Heatmap',
                            'items': [
                                {
                                    'name': 'original image',
                                    'description': '분석 대상 이미지 원본입니다.'
                                },
                                {
                                    'name': 'CAM overlay image',
                                    'description': '전체 활성화 데이터 heatmap을 원본에 겹쳐서 표현한 이미지입니다.\n\n이미지 내 활성 영역의 정확한 위치를 확인할 수 있습니다.'
                                },
                                {
                                    'name': 'activation distribution',
                                    'description': '전체 활성화 데이터의 수치와 빈도에 따른 분포 히스토그램입니다.'
                                }
                            ]
                        },
                        {
                            'title': 'Statistics',
                            'items': [
                                {
                                    'name': 'cam value distribution',
                                    'description': '활성화 수치에 대한 분포 히스토그램입니다.',
                                    'sub_description': '하늘색 막대 그래프 : q75 - q25 범위에 해당하는 값\n\n주황색 선 : 중앙값\n\n흰색 점 : 이상치 (최대 활성화 값)\n\n평균, 표준편차, 범위 표기'
                                },
                                {
                                    'name': 'cam activation percentile',
                                    'description': '활성화된 CAM 값의 백분위수를 측정합니다. (0 값 제외)\n전체 활성 분포 백분위에 해당하는 값 표기\n\n분포의 치우침 정도를 알 수 있습니다.'
                                },
                                {
                                    'name': 'activation ratio w/ threshold',
                                    'description': '임계값 별 활성화 비율을 나타냅니다.\n\n임계값에 따른 변화율을 관측할 수 있습니다.'
                                },
                                {
                                    'name': 'skewness analysis',
                                    'description': '비대칭도를 분석합니다. (정규분포 기준 얼마나 벗어났는지 측정)\n\n수식 : `평균((값 - 평균) / 표준편차)³`',
                                    'sub_items': [
                                        {
                                            'name': 'skewness 해석',
                                            'items': [
                                                '오른꼬리 분포 (양수) : 낮은 활성치의 비율이 더 높음',
                                                '왼꼬리 분포 (음수) : 높은 활성치의 비율이 더 높음',
                                                '0 : 대칭 (정규분포)'
                                            ]
                                        },
                                        {
                                            'name': 'percentile skewness',
                                            'description': 'q1, q2, q3 값을 활용한 비대칭도 측정 (백분위수 기준 25% ~ 75% 값)\n\n극단값에 덜 민감하고 안정적인 분포 특성을 보여줍니다.'
                                        }
                                    ]
                                },
                                {
                                    'name': 'quality metrics',
                                    'description': '데이터 품질 관련 지표를 측정합니다.',
                                    'sub_items': [
                                        {
                                            'name': 'concentration (집중도)',
                                            'description': '`(max_val - mean_val) / (max_val - min_val)`\n\n수치가 낮을수록 분산적, 높을수록 집중적'
                                        },
                                        {
                                            'name': 'uniformity (균등성)',
                                            'description': '`1 - (std_val / max_val)`\n\n낮을수록 불규칙적, 높을수록 활성화 값이 균등하게 분포'
                                        },
                                        {
                                            'name': 'confidence (신뢰도)',
                                            'description': '`(high_activation_ratio / 100) * (mean_val / max_val)`'
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            'title': 'Threshold',
                            'description': '임계값 기반으로 활성화 데이터에 대한 스레스홀드 적용 후 활성화 영역을 관찰할 수 있습니다.\n\n활성화가 강하게 일어나는 영역을 특정할 수 있습니다.',
                            'items': [
                                {
                                    'name': 'thresholds range',
                                    'description': 'p80, p85, p90, p95'
                                }
                            ]
                        },
                        {
                            'title': 'Clustering',
                            'description': '임계값 기반 스레스홀드 적용 후 활성화 영역에 대한 클러스터링을 수행합니다.\n\n가장 많은 클러스터가 관측되는 임계값에 대한 결과를 출력합니다.'
                        },
                        {
                            'title': 'Entropy',
                            'description': '활성화 데이터에 대한 엔트로피를 측정합니다.',
                            'items': [
                                {
                                    'name': 'histogram entropy',
                                    'code': 'hist, _ = np.histogram(non_zero_values, bins=50, density=True)\nentropy_val = entropy(hist + 1e-10)  # 0 방지',
                                    'description': '엔트로피가 낮을수록 집중적, 높을수록 분산적인 분포\n\n최소 활성값이 높을수록 노이즈 작다고 판단할 수 있음\n\n분포 모양에 따라 오른꼬리/왼꼬리 분포로 나누어 판단할 수 있음'
                                },
                                {
                                    'name': 'spatial entropy',
                                    'code': '# 그래디언트 계산 (중앙 차분 방식)\ngx = np.zeros_like(cam)\ngy = np.zeros_like(cam)\n\n# 수평 그래디언트 (Gx) - 중앙 차분\ngx[:, 1:-1] = (cam[:, 2:] - cam[:, :-2]) / 2.0\n\n# 수직 그래디언트 (Gy) - 중앙 차분\ngy[1:-1, :] = (cam[2:, :] - cam[:-2, :]) / 2.0\n\n# 그래디언트 크기 (magnitude)\ngradient_magnitude = np.sqrt(gx**2 + gy**2)\n\n# 각 방향별 엔트로피 계산\ngx_ent = shannon_entropy((gx * 255).astype(np.uint8))\ngy_ent = shannon_entropy((gy * 255).astype(np.uint8))\nmagnitude_ent = shannon_entropy((gradient_magnitude * 255).astype(np.uint8))\n\n# 평균 공간 엔트로피 (그래디언트 크기에 더 높은 가중치)\nspatial_ent = 0.4 * gx_ent + 0.4 * gy_ent + 0.2 * magnitude_ent',
                                    'description': '엔트로피가 낮을수록 단순한 패턴과 특정 값 집중, 높을수록 균등한 활성 분포와 복잡한 패턴\n\n붉은색 부분이 활성화 값이 급격히 변하는 영역\n\n패턴의 종류 : 중앙 집중형(핫스팟) 패턴, 선형 패턴, 대칭 패턴'
                                },
                                {
                                    'name': 'conditional entropy',
                                    'description': '임계값 이상 활성치 데이터에 대한 조건부 엔트로피 계산\n\n영역이 좁아짐에 따라 자연스럽게 엔트로피 상승',
                                    'code': 'threshold_val = np.percentile(cam, thresh)\nactive_mask = cam > threshold_val\ninactive_mask = cam <= threshold_val\n\nactive_ratio = np.sum(active_mask) / cam.size\n\nconditional_ent = active_ratio * active_ent + (1 - active_ratio) * inactive_ent',
                                    'sub_description': '임계값이 높을수록 비활성 영역 커짐, 범위 증가에 따른 가중 비율 상승 ⇒ 엔트로피 상승\n\n활성화 수치의 분포, 영역의 분포 특성에 따라 엔트로피가 오히려 감소하거나 변화율이 급변할 수 있음'
                                }
                            ]
                        },
                        {
                            'title': 'Centroid',
                            'items': [
                                {
                                    'name': 'max centroid',
                                    'code': 'confidence = max_activation / theoretical_max\n# 신뢰도 수치 자체는 대체로 높을 수 밖에 없음',
                                    'description': '가장 높은 활성화 값을 가진 단일 픽셀 위치\n\nspurious correlation 에 취약함'
                                },
                                {
                                    'name': 'components centroid',
                                    'code': 'confidence = component_strength * component_size\n# 연결된 컴포넌트의 크기와 강도',
                                    'description': '여러 활성화 영역을 고려한 중심점\n\n안정적이고 강건한 방식'
                                },
                                {
                                    'name': 'weighted centroid',
                                    'code': 'confidence = mean_activation / max_activation if max_activation > 0 else 0\n# 전체 활성화 강도 대비 평균 활성화 강도',
                                    'description': '가중 평균 기반 중심점\n\n활성화 패턴이 분산적일 경우 신뢰도 하락'
                                },
                                {
                                    'name': 'threshold centroid',
                                    'code': 'confidence = active_ratio * active_intensity\n# 임계값 이상 활성화된 영역의 비율과 강도',
                                    'description': '임계값 기반 중심점\n\n영역 위치에 대한 고려 없음'
                                },
                                {
                                    'name': 'coordinate distribution',
                                    'description': '계산 방법에 따른 중심 좌표의 분포 분석',
                                    'sub_description': '하늘색 막대 (x coordinate value) : x 좌표의 범위\n\n분홍색 막대 (y coordinate value) : y 좌표의 범위\n\n빈도 (frequency) : 각 범위에 해당하는 중심 좌표의 갯수 (최대 4)'
                                }
                            ]
                        },
                        {
                            'title': 'Overlap',
                            'items': [
                                {
                                    'name': 'IoU',
                                    'description': 'Intersection / Union\n\n활성 영역과 GT bbox의 겹침 정도'
                                },
                                {
                                    'name': 'CAM coverage',
                                    'code': 'cam_coverage = intersection_area / bbox_area if bbox_area > 0 else 0\n# gt bbox 영역 중 cam 영역과 겹치는 비율',
                                    'description': 'bbox 내에서 cam 활성 영역이 차지하는 비율'
                                },
                                {
                                    'name': 'BBOX coverage',
                                    'code': 'bbox_coverage = intersection_area / cam_active_area if cam_active_area > 0 else 0\n# cam 영역 중 gt bbox와 겹치는 비율',
                                    'description': 'cam 영역 내에서 bbox가 차지하는 비율'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    
    def generate_html_guideline(self):
        """XAI 가이드라인을 HTML 형태로 생성합니다."""
        html_parts = []
        
        # 헤더
        html_parts.append(f"""
        <div style="max-width: 1200px; margin: 0 auto; padding: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 2.5em; font-weight: 300;">{self.guideline_data['title']}</h1>
            </div>
        """)
        
        # 목차
        html_parts.append("""
        <div style="background: #f8f9fa; padding: 25px; border-radius: 10px; margin-bottom: 30px; border-left: 5px solid #667eea;">
            <h2 style="color: #495057; margin-top: 0; margin-bottom: 20px;">📚 목차</h2>
            <ul style="list-style: none; padding: 0; margin: 0;">
        """)
        
        for section in self.guideline_data['sections']:
            html_parts.append(f"""
                <li style="margin-bottom: 10px;">
                    <a href="#section-{section['title'].replace(' ', '-').lower()}" 
                       style="color: #667eea; text-decoration: none; font-weight: 500; display: block; padding: 8px 15px; border-radius: 5px; transition: background-color 0.3s;"
                       onmouseover="this.style.backgroundColor='#e9ecef'" 
                       onmouseout="this.style.backgroundColor='transparent'">
                        📊 {section['title']}
                    </a>
                </li>
            """)
            
            if 'subsections' in section:
                for i, subsection in enumerate(section['subsections']):
                    html_parts.append(f"""
                        <li style="margin-bottom: 5px; margin-left: 20px;">
                            <a href="#subsection-{section['title'].replace(' ', '-').lower()}-{i}" 
                               style="color: #6c757d; text-decoration: none; font-size: 0.9em; display: block; padding: 5px 15px; border-radius: 5px; transition: background-color 0.3s;"
                               onmouseover="this.style.backgroundColor='#e9ecef'" 
                               onmouseout="this.style.backgroundColor='transparent'">
                                🔍 {subsection['title']}
                            </a>
                        </li>
                    """)
        
        html_parts.append("""
            </ul>
        </div>
        """)
        
        # 메인 콘텐츠
        for section in self.guideline_data['sections']:
            html_parts.append(f"""
            <div id="section-{section['title'].replace(' ', '-').lower()}" style="margin-bottom: 40px;">
                <h2 style="color: #495057; margin-bottom: 25px; padding-bottom: 10px; border-bottom: 3px solid #667eea; font-size: 2em;">
                    📊 {section['title']}
                </h2>
            """)
            
            if 'subsections' in section:
                for i, subsection in enumerate(section['subsections']):
                    html_parts.append(f"""
                    <div id="subsection-{section['title'].replace(' ', '-').lower()}-{i}" style="margin-bottom: 30px; padding: 25px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 5px solid #28a745;">
                        <h3 style="color: #495057; margin-top: 0; margin-bottom: 20px; font-size: 1.5em;">
                            🔍 {subsection['title']}
                        </h3>
                    """)
                    
                    # 설명이 있는 경우
                    if 'description' in subsection:
                        # 줄바꿈을 <br> 태그로 변환하고 코드 블록 처리
                        section_description_html = subsection['description'].replace('\n\n', '</p><p style="margin: 0; color: #495057; font-size: 1.1em;">').replace('\n', '<br>')
                        # 백틱으로 감싸진 코드를 인라인 코드 스타일로 변환
                        section_description_html = re.sub(r'`([^`]+)`', r'<code style="background: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: monospace; color: #e83e8c;">\1</code>', section_description_html)
                        html_parts.append(f"""
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #17a2b8;">
                            <p style="margin: 0; color: #495057; font-size: 1.1em;">{section_description_html}</p>
                        </div>
                        """)
                    
                    # 아이템들이 있는 경우
                    if 'items' in subsection:
                        for item in subsection['items']:
                            html_parts.append(f"""
                            <div style="margin-bottom: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;">
                                <h4 style="color: #495057; margin-top: 0; margin-bottom: 15px; font-size: 1.2em; display: flex; align-items: center;">
                                    <span style="background: #667eea; color: white; padding: 3px 8px; border-radius: 15px; font-size: 0.8em; margin-right: 10px;">📌</span>
                                    {item['name']}
                                </h4>
                            """)
                            
                            # 설명
                            if 'description' in item:
                                # 줄바꿈을 <br> 태그로 변환하고 코드 블록 처리
                                description_html = item['description'].replace('\n\n', '</p><p style="color: #6c757d; margin-bottom: 15px; line-height: 1.6;">').replace('\n', '<br>')
                                # 백틱으로 감싸진 코드를 인라인 코드 스타일로 변환
                                description_html = re.sub(r'`([^`]+)`', r'<code style="background: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: monospace; color: #e83e8c;">\1</code>', description_html)
                                html_parts.append(f"""
                                <p style="color: #6c757d; margin-bottom: 15px; line-height: 1.6;">{description_html}</p>
                                """)
                            
                            # 코드가 있는 경우
                            if 'code' in item:
                                html_parts.append(f"""
                                <div style="background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 8px; margin: 15px 0; font-family: 'Courier New', monospace; font-size: 0.9em; overflow-x: auto;">
                                    <pre style="margin: 0; white-space: pre-wrap;">{item['code']}</pre>
                                </div>
                                """)
                            
                            # 서브 설명이 있는 경우
                            if 'sub_description' in item:
                                # 줄바꿈을 <br> 태그로 변환
                                sub_desc_html = item['sub_description'].replace('\n\n', '</p><p style="margin: 0; color: #856404; font-style: italic;">💡 ').replace('\n', '<br>')
                                html_parts.append(f"""
                                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin-top: 15px;">
                                    <p style="margin: 0; color: #856404; font-style: italic;">💡 {sub_desc_html}</p>
                                </div>
                                """)
                            
                            # 서브 아이템들이 있는 경우
                            if 'sub_items' in item:
                                html_parts.append("""
                                <div style="margin-top: 15px;">
                                """)
                                
                                for sub_item in item['sub_items']:
                                    if isinstance(sub_item, dict):
                                        if 'name' in sub_item:
                                            html_parts.append(f"""
                                            <div style="margin-bottom: 10px;">
                                                <h5 style="color: #495057; margin-bottom: 8px; font-size: 1em;">
                                                    <span style="background: #ffc107; color: #212529; padding: 2px 6px; border-radius: 10px; font-size: 0.8em; margin-right: 8px;">🔹</span>
                                                    {sub_item['name']}
                                                </h5>
                                            """)
                                            
                                            if 'description' in sub_item:
                                                # 줄바꿈을 <br> 태그로 변환하고 코드 블록 처리
                                                sub_description_html = sub_item['description'].replace('\n\n', '</p><p style="color: #6c757d; margin-bottom: 10px; margin-left: 20px; font-size: 0.95em;">').replace('\n', '<br>')
                                                # 백틱으로 감싸진 코드를 인라인 코드 스타일로 변환
                                                sub_description_html = re.sub(r'`([^`]+)`', r'<code style="background: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: monospace; color: #e83e8c;">\1</code>', sub_description_html)
                                                html_parts.append(f"""
                                                <p style="color: #6c757d; margin-bottom: 10px; margin-left: 20px; font-size: 0.95em;">{sub_description_html}</p>
                                                """)
                                            
                                            if 'items' in sub_item:
                                                html_parts.append("""
                                                <ul style="margin-left: 20px; color: #6c757d;">
                                                """)
                                                for sub_sub_item in sub_item['items']:
                                                    html_parts.append(f"""
                                                    <li style="margin-bottom: 5px;">{sub_sub_item}</li>
                                                    """)
                                                html_parts.append("</ul>")
                                            
                                            html_parts.append("</div>")
                                    else:
                                        # 단순 문자열인 경우
                                        html_parts.append(f"""
                                        <div style="margin-bottom: 8px; margin-left: 20px;">
                                            <span style="color: #6c757d;">• {sub_item}</span>
                                        </div>
                                        """)
                                
                                html_parts.append("</div>")
                            
                            html_parts.append("</div>")
                    
                    html_parts.append("</div>")
            
            html_parts.append("</div>")
        
        # 푸터
        html_parts.append(f"""
        <div style="background: #f8f9fa; padding: 30px; border-radius: 10px; text-align: center; margin-top: 40px; border-top: 3px solid #667eea;">
            <p style="margin: 0; color: #6c757d; font-size: 0.9em;">
                📄 이 가이드라인은 XAI 분석 결과를 해석하는 데 도움을 주기 위해 작성되었습니다.<br>
                🔄 최종 업데이트: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}
            </p>
        </div>
        </div>
        """)
        
        return ''.join(html_parts)
    
    def save_guideline_html(self, output_path):
        """가이드라인을 HTML 파일로 저장합니다."""
        html_content = self.generate_html_guideline()
        
        # 완전한 HTML 문서 구조
        full_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XAI Report Guideline</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        
        .header .meta {{
            margin-top: 15px;
            opacity: 0.9;
        }}
        
        .header .meta span {{
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            margin-right: 15px;
        }}
        
        .toc {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            border-left: 5px solid #667eea;
        }}
        
        .toc h2 {{
            color: #495057;
            margin-top: 0;
            margin-bottom: 20px;
        }}
        
        .toc ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .toc li {{
            margin-bottom: 10px;
        }}
        
        .toc a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            display: block;
            padding: 8px 15px;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        
        .toc a:hover {{
            background-color: #e9ecef;
        }}
        
        .toc li li {{
            margin-bottom: 5px;
            margin-left: 20px;
        }}
        
        .toc li li a {{
            color: #6c757d;
            font-size: 0.9em;
            padding: 5px 15px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #495057;
            margin-bottom: 25px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            font-size: 2em;
        }}
        
        .subsection {{
            margin-bottom: 30px;
            padding: 25px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 5px solid #28a745;
        }}
        
        .subsection h3 {{
            color: #495057;
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        
        .description {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #17a2b8;
        }}
        
        .description p {{
            margin: 0;
            color: #495057;
            font-size: 1.1em;
        }}
        
        .item {{
            margin-bottom: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        
        .item h4 {{
            color: #495057;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.2em;
            display: flex;
            align-items: center;
        }}
        
        .item h4 span {{
            background: #667eea;
            color: white;
            padding: 3px 8px;
            border-radius: 15px;
            font-size: 0.8em;
            margin-right: 10px;
        }}
        
        .item p {{
            color: #6c757d;
            margin-bottom: 15px;
            line-height: 1.6;
        }}
        
        .code-block {{
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }}
        
        .code-block pre {{
            margin: 0;
            white-space: pre-wrap;
        }}
        
        .note {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        .note p {{
            margin: 0;
            color: #856404;
            font-style: italic;
        }}
        
        .sub-item {{
            margin-bottom: 10px;
        }}
        
        .sub-item h5 {{
            color: #495057;
            margin-bottom: 8px;
            font-size: 1em;
        }}
        
        .sub-item h5 span {{
            background: #ffc107;
            color: #212529;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.8em;
            margin-right: 8px;
        }}
        
        .sub-item p {{
            color: #6c757d;
            margin-bottom: 10px;
            margin-left: 20px;
            font-size: 0.95em;
        }}
        
        .sub-item ul {{
            margin-left: 20px;
            color: #6c757d;
        }}
        
        .sub-item li {{
            margin-bottom: 5px;
        }}
        
        .simple-item {{
            margin-bottom: 8px;
            margin-left: 20px;
        }}
        
        .simple-item span {{
            color: #6c757d;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-top: 40px;
            border-top: 3px solid #667eea;
        }}
        
        .footer p {{
            margin: 0;
            color: #6c757d;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .header .meta span {{
                display: block;
                margin-bottom: 10px;
                margin-right: 0;
            }}
            
            .subsection {{
                padding: 15px;
            }}
            
            .item {{
                padding: 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        print(f"✅ XAI 가이드라인이 성공적으로 생성되었습니다: {output_path}")


class ChartDescriptionGenerator:
    """차트 설명을 생성하고 관리하는 클래스"""
    
    def __init__(self):
        self.descriptions = self._initialize_descriptions()
    
    def _initialize_descriptions(self):
        """모든 차트 설명을 초기화"""
        return {
            # === 이미지 속성 분석 차트 ===
            'file_size_distribution': {
                'title': '파일 크기 분포',
                'description': '이 차트는 데이터셋 내 이미지들의 파일 크기 분포를 히스토그램 형태로 시각화합니다. 가로축은 파일 크기를 메가바이트(MB) 단위로 표시하고, 세로축은 해당 크기 구간에 속하는 이미지의 개수를 나타냅니다. 각 막대는 특정 크기 구간의 이미지 수량을 의미하며, 이 차트를 통해 데이터셋의 저장 공간 사용 패턴을 파악할 수 있습니다. 저장 공간 최적화 전략 수립과 데이터 품질 평가에 중요한 정보를 제공합니다.',
                'category': 'image_attributes'
            },
            
            'image_format_distribution': {
                'title': '이미지 형식 분포',
                'description': '이 차트는 데이터셋에서 사용되는 이미지 형식의 분포를 파이 차트 형태로 시각화합니다. 각 조각은 특정 이미지 형식(JPEG, PNG, GIF 등)을 나타내며, 조각의 크기는 해당 형식이 차지하는 비율을 의미합니다. 이 차트를 통해 데이터셋의 형식 다양성과 일관성을 확인할 수 있으며, 모델 학습 시 형식별 전처리 전략을 수립하는 데 중요한 정보를 제공합니다.',
                'category': 'image_attributes'
            },
            
            'resolution_distribution': {
                'title': '해상도 분포',
                'description': '이 차트는 데이터셋 내 이미지들의 해상도 분포를 막대 차트 형태로 시각화합니다. 가로축은 이미지의 해상도(가로 픽셀 × 세로 픽셀)를 표시하고, 세로축은 해당 해상도를 가진 이미지의 개수를 나타냅니다. 각 막대는 특정 해상도를 가진 이미지의 수량을 의미하며, 이 차트를 통해 데이터셋의 해상도 다양성을 확인할 수 있습니다. 모델 학습 데이터의 품질과 전처리 필요성을 평가하는 데 중요한 정보를 제공합니다.',
                'category': 'image_attributes'
            },
            
            'noise_vs_sharpness': {
                'title': '노이즈 vs 엣지니스',
                'description': '이 차트는 이미지의 노이즈 레벨과 엣지니스라는 두 가지 품질 속성 간의 관계를 산점도 형태로 시각화합니다. 가로축은 노이즈 레벨을, 세로축은 엣지니스 값을 나타내며, 각 점은 개별 이미지를 의미합니다. 이 차트를 통해 두 속성 간의 상관관계를 파악할 수 있으며, 데이터 전처리 시 노이즈 제거의 필요성과 이미지 품질 개선 포인트를 파악할 수 있습니다.',
                'category': 'image_attributes'
            },
            
            # === 임베딩 분석 차트 ===
            'embeddings_pca': {
                'title': 'PCA 2D 임베딩',
                'description': '이 차트는 고차원 이미지 임베딩 데이터를 주성분 분석(PCA)을 통해 2차원으로 축소한 결과를 산점도 형태로 시각화합니다. 가로축과 세로축은 각각 첫 번째와 두 번째 주성분을 나타내며, 각 점은 하나의 이미지 임베딩을 의미합니다. 이 차트를 통해 이미지 간의 유사성과 군집성을 탐색할 수 있으며, 데이터의 잠재적인 구조와 패턴을 파악할 수 있습니다.',
                'category': 'embedding_analysis'
            },
            
            # === 클러스터링 분석 차트 ===
            'clustering_results': {
                'title': '클러스터링 결과',
                'description': '이 차트는 클러스터링 알고리즘을 사용하여 데이터를 그룹화한 결과를 2차원 공간에 시각화합니다. 각 점은 개별 데이터를 의미하며, 색상은 클러스터 할당 결과를 구분합니다. 클러스터 센트로이드는 X 마커와 O 마커로 표시되며, 클러스터 번호는 워터마크 스타일로 센트로이드 위치에 표시됩니다. 이 차트를 통해 클러스터 간의 분리도와 응집도를 시각적으로 확인하고, 데이터의 그룹화 패턴을 파악할 수 있습니다.',
                'category': 'clustering_analysis'
            },
            
            'cluster_size_distribution': {
                'title': '클러스터 분포',
                'description': '이 차트는 클러스터링 결과에서 각 클러스터에 속하는 데이터의 개수를 막대 차트 형태로 시각화합니다. 가로축은 클러스터 번호를, 세로축은 해당 클러스터에 속하는 데이터의 개수를 나타내며, 각 막대는 특정 클러스터의 크기를 의미합니다. 이 차트를 통해 클러스터링 결과의 균형과 각 클러스터의 대표성을 평가할 수 있으며, 데이터의 그룹화 패턴을 확인할 수 있습니다.',
                'category': 'clustering_analysis'
            },
            
            # === XAI 분석 차트 ===
            'cam_distribution': {
                'title': 'CAM 분포',
                'description': '이미지는 원본 이미지 위에 CAM(Class Activation Map)을 히트맵 형태로 시각화합니다. 히트맵은 빨간색(가장 높은 활성화)부터 파란색(가장 낮은 활성화)까지의 색상 스펙트럼을 사용하여, 모델이 특정 예측을 내리는 데 가장 중요하게 고려한 이미지 영역을 시각적으로 강조합니다. 이 오버레이는 모델이 이미지의 어느 부분에 집중하고 있는지를 직관적으로 이해하는 데 도움을 줍니다.<br><br>차트는 CAM 활성화 값의 통계적 분포를 히스토그램 형태로 보여줍니다. 가로축은 활성화 값을 0.0부터 1.0까지의 범위로 나타내며, 세로축은 해당 활성화 값 범위에 속하는 픽셀의 빈도를 표시합니다. 차트 좌측 상단에는 평균, 표준편차, 최대값과 같은 주요 통계와 특정 임계값을 초과하는 활성화 영역의 비율이 요약되어 있습니다. 이 분포는 CAM 값들이 이미지 전체에 걸쳐 어떻게 퍼져 있는지, 즉 모델의 활성화가 특정 영역에 집중되어 있는지 또는 넓게 분포되어 있는지를 파악하는 데 중요한 정보를 제공합니다.',
                'category': 'xai_analysis'
            },
            
            'cam_statistics': {
                'title': 'CAM 통계',
                'description': '이 차트는 CAM(Class Activation Map) 값의 통계적 특성을 네 가지 관점에서 시각화합니다.<br><br>첫 번째 차트는 CAM 값의 전체 분포를 박스 플롯으로 보여주며, 중앙값, 사분위수 범위, 이상치를 통해 CAM 값들이 어떻게 퍼져 있는지를 파악할 수 있습니다.<br><br>두 번째 차트는 CAM 활성화 값의 백분위수 분포를 막대 차트로 표시하여 활성화 값이 낮은 값에서 높은 값으로 어떻게 누적되는지를 확인할 수 있습니다.<br><br>세 번째 차트는 임계값의 변화에 따른 활성화 비율의 변화를 선 그래프로 보여주며, CAM을 이진화하거나 특정 활성화 영역을 추출할 때 적절한 임계값을 설정하는 데 도움을 줍니다.<br><br>네 번째 차트는 CAM 값 분포의 왜도를 두 가지 방법으로 계산하여 데이터 분포가 어느 한쪽으로 치우쳐 있는지를 파악할 수 있습니다.<br><br>다섯 번째 차트는 CAM 분석의 품질을 평가하는 세 가지 핵심 지표를 막대 차트로 시각화합니다. 집중도(Concentration)는 CAM이 특정 영역에 얼마나 집중되어 있는지를 나타내며, 균일도(Uniformity)는 활성화 영역이 얼마나 균일하게 분포되어 있는지를 보여줍니다. 신뢰도(Confidence)는 활성화 영역이 모델의 예측과 얼마나 일치하는지를 점수로 표현합니다.',
                'category': 'xai_analysis'
            },
            
            'adaptive_cam_analysis': {
                'title': '적응형 CAM 분석',
                'description': '이 차트는 다양한 적응형 비율(80%, 85%, 90%, 95%)에 따른 CAM 분석 결과를 비교합니다.<br><br>첫 번째 행은 적응형 히트맵으로 특정 값의 공간적 분포를 시각화하며, 적응형 비율이 증가함에 따라 활성화된 영역이 점차 작아지고 더 집중되는 경향을 보입니다.<br><br>두 번째 행은 적응형 값의 빈도 분포를 히스토그램으로 보여주며, 비율이 증가할수록 분포가 높은 값 쪽으로 이동하고 더 좁아지는 경향을 나타냅니다.<br><br>세 번째 행은 원본 이미지 위에 CAM을 오버레이하여 모델이 이미지의 어느 부분을 보고 특정 결정을 내렸는지를 시각적으로 보여줍니다. 이 차트를 통해 적응형 임계값 설정이 CAM 분석 결과에 미치는 영향을 파악할 수 있습니다.',
                'category': 'xai_analysis'
            },
            
            'connected_components_analysis': {
                'title': '연결 구성 요소 분석',
                'description': '이 차트는 CAM 활성화 영역의 연결 구성 요소를 분석하여 시각화합니다.<br><br>첫 번째 차트는 활성화 비율을 파이 차트로 보여주며, 활성 픽셀과 비활성 픽셀의 비율을 명확하게 표시합니다.<br><br>두 번째 차트는 레이블이 지정된 구성 요소를 분할 맵으로 시각화하여 각 구성 요소의 공간적 분포와 상대적 크기를 보여줍니다.<br><br>세 번째 차트는 구성 요소 크기 통계를 막대 차트로 표시하여 최대, 최소, 평균, 중앙값, 표준편차 등의 통계적 특성을 파악할 수 있습니다.<br><br>네 번째 차트는 연결 구성 요소 분석에 대한 상세한 수치 요약을 제공하여 활성 픽셀 수, 활성 비율, 구성 요소 수, 임계값 등의 정보를 확인할 수 있습니다.',
                'category': 'xai_analysis'
            },
            
            'cam_entropy_analysis': {
                'title': '엔트로피 분석',
                'description': '이 차트는 CAM 값의 엔트로피와 공간적 특성을 네 가지 관점에서 분석합니다.<br><br>첫 번째 차트는 0이 아닌 CAM 값의 분포를 히스토그램으로 보여주며, 히스토그램 엔트로피와 활성화 비율을 계산하여 CAM 값의 복잡성을 평가합니다.<br><br>두 번째 차트는 CAM 값의 공간적 차이(그라디언트)를 히트맵으로 시각화하여 공간적 엔트로피를 계산하고, CAM 값의 공간적 변화가 가장 큰 영역을 식별합니다.<br><br>세 번째 차트는 임계값 백분위수에 따른 조건부 엔트로피의 변화를 선 그래프로 보여주며, 임계값 설정이 엔트로피에 미치는 영향을 분석합니다.<br><br>네 번째 차트는 가로, 세로, 전체 크기 방향에 따른 공간적 엔트로피를 막대 그래프로 비교하여 CAM의 방향별 복잡성을 평가합니다.',
                'category': 'xai_analysis'
            },
            
            'cam_centroid_analysis': {
                'title': '센트로이드 분석',
                'description': '이 차트는 CAM 활성화 영역의 센트로이드를 다양한 방법론으로 계산하고 분석합니다.<br><br>첫 번째 차트는 원본 이미지 위에 CAM 히트맵과 계산된 센트로이드를 오버레이하여 모델이 집중하는 영역과 해당 영역의 중심점을 시각적으로 보여줍니다.<br><br>두 번째 차트는 다양한 센트로이드 계산 방법론에 대한 신뢰도 점수를 막대 차트로 비교하여 가장 신뢰할 수 있는 방법을 식별합니다.<br><br>세 번째 차트는 센트로이드 분석에 대한 요약 정보와 각 방법론에 대한 설명을 텍스트로 제공하여 분석 결과를 이해하는 데 도움을 줍니다.<br><br>네 번째 차트는 활성화된 픽셀들의 가로 및 세로 좌표 분포를 히스토그램으로 보여주어 활성화 영역의 공간적 특성을 분석합니다.',
                'category': 'xai_analysis'
            },
            
            'object_detection_cam_overlay': {
                'title': '오버레이 분석',
                'description': '이 차트는 객체 감지 결과와 CAM 분석을 결합하여 모델의 주의 집중과 객체 감지 간의 일치성을 시각화합니다.<br><br>첫 번째 차트는 입력 이미지를 원본 그대로 표시하여 분석의 기준점을 제공합니다.<br><br>두 번째 차트는 CAM 히트맵을 어두운 배경 위에 표시하여 모델이 특정 클래스 예측에 가장 강하게 영향을 미친 이미지 영역을 색상 그라데이션으로 강조합니다.<br><br>세 번째 차트는 모든 감지된 객체를 바운딩 박스로 표시하며, 가장 큰 객체는 빨간색으로 특별히 강조하여 모델이 식별한 객체들과 그 중 가장 중요한 객체를 구분합니다.<br><br>네 번째 차트는 CAM 활성화 영역을 이진 마스크로 표시하여 모델이 주의를 기울인 영역을 명확하게 분할합니다.<br><br>다섯 번째 차트는 가장 큰 감지된 바운딩 박스 영역만을 마스크로 표시하여 주요 객체의 공간적 범위를 격리합니다.<br><br>여섯 번째 차트는 CAM 활성 영역과 가장 큰 바운딩 박스 영역의 겹침을 시각화하여 IoU 점수로 정량적 평가를 제공합니다.',
                'category': 'xai_analysis'
            },
            
            'object_detection_performance_summary': {
                'title': '겹침 통계',
                'description': '이 차트는 객체 감지 모델의 성능과 설명 가능성을 평가하는 핵심 지표들을 요약하여 표시합니다.<br><br>첫 번째 차트는 Intersection over Union(IoU) 점수를 막대 그래프로 시각화하여 예측된 바운딩 박스와 실제 바운딩 박스 간의 겹침 정도를 측정합니다.<br><br>두 번째 차트는 CAM 커버리지와 바운딩 박스 커버리지를 막대 그래프로 비교하여 모델의 설명 가능성과 객체 감지 영역의 포괄성을 평가합니다.<br><br>세 번째 차트는 감지된 객체 정보와 종합 요약을 텍스트로 제공하여 특정 객체 감지 결과의 세부 사항과 전체적인 성능 평가를 한눈에 파악할 수 있게 합니다.<br><br>이 차트를 통해 모델의 객체 감지 정확도와 해석 가능성을 종합적으로 평가할 수 있으며, 개선이 필요한 영역을 식별하는 데 도움을 줍니다.',
                'category': 'xai_analysis'
            }
        }
    
    def get_description(self, chart_key):
        """특정 차트의 설명 반환"""
        return self.descriptions.get(chart_key, {})
    
    def get_descriptions_by_category(self, category):
        """카테고리별 차트 설명 반환"""
        return {k: v for k, v in self.descriptions.items() if v.get('category') == category}
    
    def generate_description_html(self, chart_key):
        """차트 설명을 HTML로 생성"""
        desc = self.get_description(chart_key)
        if not desc:
            return ""
            
        return f"""
        <div class="chart-description">
            <div class="description-header">
                <span class="description-icon">📊</span>
                <span class="description-title">설명</span>
            </div>
            <div class="description-content">
                {desc['description']}
            </div>
        </div>
        """
    
    def generate_category_summary(self, category):
        """카테고리별 차트 설명 요약 생성"""
        category_descriptions = self.get_descriptions_by_category(category)
        if not category_descriptions:
            return ""
            
        html_parts = [f'<h3>{category.replace("_", " ").title()} 차트 설명</h3>']
        for chart_key, desc in category_descriptions.items():
            html_parts.append(f"""
            <div class="chart-description-summary">
                <h4>{desc['title']}</h4>
                <p>{desc['description']}</p>
            </div>
            """)
        
        return ''.join(html_parts)


def create_xai_guideline(output_path="xai_guideline.html"):
    """XAI 가이드라인을 생성하고 저장합니다."""
    generator = XAIGuidelineGenerator()
    generator.save_guideline_html(output_path)
    return output_path

if __name__ == "__main__":
    # 현재 디렉토리에 가이드라인 생성
    output_file = create_xai_guideline()
    print(f"📄 가이드라인 파일이 생성되었습니다: {output_file}")
