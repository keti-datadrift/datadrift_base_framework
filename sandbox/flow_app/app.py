# flow_app/app.py
import dash
import dash_cytoscape as cyto
import networkx as nx
import pluggy
from dash import dcc, html, Input, Output, State, no_update

# 1. 후크 명세 모듈(hooks)과 플러그인 모듈(plugins)을 임포트합니다.
import flow_app.hooks
from flow_app.plugins.csv_loader import run_module as run_csv_loader
from flow_app.plugins.visualizer import run_module as run_visualizer

# 2. Pluggy 플러그인 매니저 설정
pm = pluggy.PluginManager("flow_app")

# 3. 후크 명세가 정의된 모듈(flow_app.hooks)을 등록합니다.
#    add_hookspecs()는 모듈을 인자로 받습니다.
pm.add_hookspecs(flow_app.hooks)

# 4. 플러그인 구현체(run_module 함수들)를 등록합니다.
#    register()는 실제 구현 함수를 인자로 받습니다.
pm.register(run_csv_loader, name='csv_loader_plugin')
pm.register(run_visualizer, name='visualizer_plugin')


app = dash.Dash(__name__)

# 초기 노드 정의
initial_elements = [
    {'data': {'id': 'csv_loader', 'label': 'CSV 파일 로더', 'type': 'csv_loader'}},
    {'data': {'id': 'visualizer', 'label': '데이터 시각화', 'type': 'visualizer'}}
]

app.layout = html.Div([
    html.H1("웹 기반 플로우 빌더"),
    html.P("노드를 드래그하여 연결하고, '실행' 버튼을 누르세요."),
    
    cyto.Cytoscape(
        id='cytoscape-flow',
        layout={'name': 'preset'},
        style={'width': '100%', 'height': '400px', 'border': '1px solid black'},
        elements=initial_elements,
        stylesheet=[
            {
                'selector': 'node',
                'style': {
                    'label': 'data(label)',
                    'background-color': '#4CAF50',
                    'color': 'white',
                    'text-valign': 'center',
                    'font-size': '12px'
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'width': 3,
                    'line-color': '#ccc',
                    'curve-style': 'bezier',
                    'target-arrow-shape': 'triangle',
                    'target-arrow-color': '#ccc'
                }
            }
        ]
    ),
    
    html.Button("플로우 실행", id='run-button', n_clicks=0, style={'margin-top': '10px'}),
    
    html.Hr(),
    html.H3("실행 결과"),
    html.Div(id='output-area')
])

@app.callback(
    Output('output-area', 'children'),
    Input('run-button', 'n_clicks'),
    State('cytoscape-flow', 'elements')
)
def run_flow(n_clicks, elements):
    if n_clicks is None or n_clicks == 0:
        return no_update

    G = nx.DiGraph()
    nodes_data = {e['data']['id']: e['data'] for e in elements if 'source' not in e['data']}
    edges_data = [(e['data']['source'], e['data']['target']) for e in elements if 'source' in e['data']]
    
    G.add_nodes_from(nodes_data.keys())
    for node_id, data in nodes_data.items():
        G.nodes[node_id].update(data)
    
    G.add_edges_from(edges_data)

    try:
        execution_order = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        return html.Div("플로우에 순환 루프가 있습니다. 올바른 순서로 연결해주세요.", style={'color': 'red'})

    print(f"실행 순서: {execution_order}")
    
    data = None
    final_output = None
    
    for node_id in execution_order:
        print(f'node_id = {node_id}')
        node_type = G.nodes[node_id]['type']
        
        # 플러그인 후크 호출
        try:
            # pm.hook.<후크명>() 형식으로 호출
            result = pm.hook.run_module(data=data)
            print('module = ', pm.hook.run_module)
            print(result)
            
            data = result
            final_output = result
            
        except Exception as e:
            return html.Div(f"모듈 '{node_type}' 실행 중 오류 발생: {e}", style={'color': 'red'})

    print(f'final_output = {final_output}')
    return final_output

if __name__ == '__main__':
    app.run(debug=True)