# src/codesynapse/visualizer.py

from pyvis.network import Network
from .rules import VISUAL_RULES, NodeType, EdgeType
import json

def visualize_graph(graph, output_filename="codesynapse_graph.html", options=None):
    """networkx 그래프를 pyvis를 사용해 HTML 파일로 시각화합니다."""
    
    # 기본 옵션
    default_options = {
        "height": "100vh",
        "width": "100%",
        "directed": True,
        "notebook": False,
        "filter_menu": True,  # 필터 메뉴 추가
        "search": True,  # 검색 기능 추가
    }
    
    if options:
        default_options.update(options)
    
    net = Network(**{k: v for k, v in default_options.items() 
                    if k in ['height', 'width', 'directed', 'notebook']})
    
    # 레이아웃 및 물리 엔진 설정을 위한 옵션 딕셔너리
    physics_options = {
        "physics": {
            "enabled": True,
            "solver": "barnesHut",
            "barnesHut": {
                "gravitationalConstant": -80000,
                "centralGravity": 0.3,
                "springLength": 250,
                "springConstant": 0.001,
                "damping": 0.09,
                "avoidOverlap": 0
            },
            "stabilization": {
                "enabled": True,
                "iterations": 1000,
                "updateInterval": 100,
                "onlyDynamicEdges": False,
                "fit": True
            }
        }
    }
    
    # 레이아웃 설정
    if VISUAL_RULES["layout"]["hierarchical"]:
        layout_options = {
            "layout": {
                "hierarchical": {
                    "enabled": True,
                    "direction": VISUAL_RULES["layout"].get("direction", "UD"),
                    "sortMethod": VISUAL_RULES["layout"].get("sort_method", "directed"),
                    "levelSeparation": 150,
                    "nodeSpacing": 100,
                    "treeSpacing": 200,
                    "blockShifting": True,
                    "edgeMinimization": True,
                    "parentCentralization": True
                }
            }
        }
        # 물리 엔진과 레이아웃 옵션 병합
        combined_options = {**physics_options, **layout_options}
    else:
        combined_options = physics_options
    
    # 옵션 설정
    net.set_options(json.dumps(combined_options))
    
    # 노드 그룹 정의 (필터링용)
    node_groups = {
        NodeType.MODULE: "modules",
        NodeType.CLASS: "classes", 
        NodeType.FUNCTION: "functions",
        NodeType.EXTERNAL_LIB: "external"
    }
    
    # 노드 추가
    for node, attrs in graph.nodes(data=True):
        node_type = attrs.get("type", NodeType.FUNCTION)
        style = VISUAL_RULES["node_styles"].get(node_type, {})
        
        # 노드 이름에서 마지막 부분만 라벨로 사용
        label = node.split('.')[-1]
        
        # 툴팁 생성 (추가 정보 포함)
        tooltip_parts = [f"Full path: {node}"]
        if attrs.get("docstring"):
            tooltip_parts.append(f"Docstring: {attrs['docstring'][:100]}...")
        if attrs.get("decorators"):
            tooltip_parts.append(f"Decorators: {', '.join(attrs['decorators'])}")
        if attrs.get("is_classmethod"):
            tooltip_parts.append("Type: Class method")
        elif attrs.get("is_staticmethod"):
            tooltip_parts.append("Type: Static method")
        
        tooltip = "\n".join(tooltip_parts)
        
        # 아이콘 추가 (이모지 사용)
        icon_map = {
            NodeType.MODULE: "📦",
            NodeType.CLASS: "🏛️",
            NodeType.FUNCTION: "⚡",
            NodeType.EXTERNAL_LIB: "🌐"
        }
        
        label_with_icon = f"{icon_map.get(node_type, '')} {label}"
        
        net.add_node(
            node,
            label=label_with_icon,
            title=tooltip,
            shape=style.get("shape", "circle"),
            color=style.get("color", "#CCCCCC"),
            size=style.get("size", 10),
            group=node_groups.get(node_type, "other"),
            level=attrs.get("level", None)  # 계층 레이아웃용
        )

    # 엣지 추가
    edge_counts = {}  # 중복 엣지 처리용
    
    for source, target, attrs in graph.edges(data=True):
        edge_type = attrs.get("type", EdgeType.CALLS)
        style = VISUAL_RULES["edge_styles"].get(edge_type, {})
        
        # 엣지 식별자
        edge_id = f"{source}->{target}"
        edge_counts[edge_id] = edge_counts.get(edge_id, 0) + 1
        
        # 엣지 라벨
        edge_label = ""
        if edge_counts[edge_id] > 1:
            edge_label = f"×{edge_counts[edge_id]}"
        
        if attrs.get("decorator"):
            edge_label = f"@decorator {edge_label}".strip()
        elif attrs.get("type_hint"):
            edge_label = f"type hint {edge_label}".strip()
        elif attrs.get("star"):
            edge_label = f"* import {edge_label}".strip()
        
        # 엣지 스타일
        edge_options = {
            "color": style.get("color", "#888888"),
            "arrows": style.get("arrowhead", "to"),
        }
        
        if edge_label:
            edge_options["label"] = edge_label
            
        if style.get("style") == "dashed":
            edge_options["dashes"] = True
        elif style.get("style") == "dotted":
            edge_options["dashes"] = [2, 2]
        
        net.add_edge(source, target, **edge_options)
    
    # HTML 생성
    net.show(output_filename, notebook=False)
    
    # 검색 및 필터 기능 추가
    if default_options.get("filter_menu") or default_options.get("search"):
        _add_interactive_features(output_filename, graph)
    
    print(f"Graph has been generated: {output_filename}")

def _add_interactive_features(filename: str, graph):
    """HTML 파일에 검색 및 필터 기능 추가"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        # 파일이 없는 경우 (예: 테스트에서 mock 사용) 무시
        return
    
    # 검색 및 필터 UI 추가
    search_filter_ui = '''
    <div id="controlPanel" style="position: absolute; top: 10px; right: 10px; background: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; z-index: 1000;">
        <h4>Controls</h4>
        
        <!-- 검색 -->
        <div style="margin-bottom: 10px;">
            <input type="text" id="searchInput" placeholder="Search nodes..." style="width: 200px; padding: 5px;">
            <button onclick="searchNode()">Search</button>
            <button onclick="clearSearch()">Clear</button>
        </div>
        
        <!-- 노드 타입 필터 -->
        <div style="margin-bottom: 10px;">
            <h5>Node Types</h5>
            <label><input type="checkbox" class="nodeFilter" value="modules" checked> Modules</label><br>
            <label><input type="checkbox" class="nodeFilter" value="classes" checked> Classes</label><br>
            <label><input type="checkbox" class="nodeFilter" value="functions" checked> Functions</label><br>
            <label><input type="checkbox" class="nodeFilter" value="external" checked> External</label>
        </div>
        
        <!-- 엣지 타입 필터 -->
        <div>
            <h5>Edge Types</h5>
            <label><input type="checkbox" class="edgeFilter" value="imports" checked> Imports</label><br>
            <label><input type="checkbox" class="edgeFilter" value="calls" checked> Calls</label><br>
            <label><input type="checkbox" class="edgeFilter" value="inherits" checked> Inherits</label><br>
            <label><input type="checkbox" class="edgeFilter" value="contains" checked> Contains</label><br>
            <label><input type="checkbox" class="edgeFilter" value="defines" checked> Defines</label><br>
            <label><input type="checkbox" class="edgeFilter" value="instantiates" checked> Instantiates</label>
        </div>
    </div>
    
    <script>
    // 검색 기능
    function searchNode() {
        var searchTerm = document.getElementById('searchInput').value.toLowerCase();
        if (!searchTerm) return;
        
        var nodes = network.body.data.nodes;
        var foundNodes = nodes.get({
            filter: function(item) {
                return item.id.toLowerCase().includes(searchTerm) || 
                       item.label.toLowerCase().includes(searchTerm);
            }
        });
        
        if (foundNodes.length > 0) {
            network.selectNodes(foundNodes.map(n => n.id));
            network.focus(foundNodes[0].id, {scale: 1.5, animation: true});
        } else {
            alert('No nodes found matching: ' + searchTerm);
        }
    }
    
    function clearSearch() {
        document.getElementById('searchInput').value = '';
        network.unselectAll();
    }
    
    // 필터 기능
    document.querySelectorAll('.nodeFilter, .edgeFilter').forEach(function(checkbox) {
        checkbox.addEventListener('change', applyFilters);
    });
    
    function applyFilters() {
        // 노드 필터
        var selectedNodeTypes = Array.from(document.querySelectorAll('.nodeFilter:checked'))
            .map(cb => cb.value);
        
        var nodes = network.body.data.nodes;
        var allNodes = nodes.get();
        
        allNodes.forEach(function(node) {
            if (selectedNodeTypes.includes(node.group)) {
                nodes.update({id: node.id, hidden: false});
            } else {
                nodes.update({id: node.id, hidden: true});
            }
        });
        
        // 엣지 필터는 pyvis의 제한으로 인해 구현이 복잡함
        // 향후 개선 필요
    }
    
    // Enter 키로 검색
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') searchNode();
    });
    </script>
    '''
    
    # </body> 태그 앞에 UI 삽입
    html_content = html_content.replace('</body>', search_filter_ui + '</body>')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)