"""
Enhanced Metadata Service with lineage tracking capabilities
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
import networkx as nx
from rich import print


@dataclass
class LineageNode:
    """계보 노드 정보"""
    id: str
    type: str  # 'dataset', 'analysis', 'experiment'
    name: str
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class LineageEdge:
    """계보 엣지 정보"""
    source: str
    target: str
    relationship: str  # 'uses', 'generates', 'depends_on'
    metadata: Dict[str, Any]


class MetadataService:
    """
    Enhanced metadata service with lineage tracking capabilities
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.metadata_dir = self.project_root / ".ddoc_metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        
        self.lineage_file = self.metadata_dir / "lineage.json"
        self.dataset_mapping_file = self.metadata_dir / "dataset_mappings.json"
        self.graph = nx.DiGraph()
        
        # Cache for metadata files (mtime-based invalidation)
        self._dataset_mappings_cache = None
        self._dataset_mappings_mtime = None
        self._lineage_cache = None
        self._lineage_mtime = None
        
        self._init_lineage()
        self._init_dataset_mappings()
        # Don't load lineage at init - lazy load when needed
        self._lineage_loaded = False
    
    def _init_lineage(self):
        """Initialize lineage file if it doesn't exist"""
        if not self.lineage_file.exists():
            lineage = {
                'datasets': {},
                'analyses': {},
                'experiments': {},
                'created_at': datetime.now().isoformat()
            }
            self._save_lineage(lineage)
    
    def _init_dataset_mappings(self):
        """Initialize dataset mappings file if it doesn't exist"""
        if not self.dataset_mapping_file.exists():
            mappings = {
                'datasets': {},
                'created_at': datetime.now().isoformat()
            }
            self._save_dataset_mappings(mappings)
    
    def _load_dataset_mappings(self) -> Dict[str, Any]:
        """Load dataset mappings with mtime-based caching"""
        if self.dataset_mapping_file.exists():
            try:
                current_mtime = self.dataset_mapping_file.stat().st_mtime
                
                # Use cache if available and file hasn't changed
                if (self._dataset_mappings_cache is not None and 
                    self._dataset_mappings_mtime == current_mtime):
                    return self._dataset_mappings_cache
                
                # Load from file
                with open(self.dataset_mapping_file, 'r') as f:
                    mappings = json.load(f)
                
                # Update cache
                self._dataset_mappings_cache = mappings
                self._dataset_mappings_mtime = current_mtime
                return mappings
            except (json.JSONDecodeError, KeyError):
                print("Warning: Could not load dataset mappings, starting fresh")
                return self._init_dataset_mappings()
        return self._init_dataset_mappings()
    
    def _save_dataset_mappings(self, mappings: Dict[str, Any] = None):
        """Save dataset mappings and invalidate cache"""
        if mappings is None:
            mappings = self._load_dataset_mappings()
        
        with open(self.dataset_mapping_file, 'w') as f:
            json.dump(mappings, f, indent=2)
        
        # Invalidate cache
        self._dataset_mappings_cache = None
        self._dataset_mappings_mtime = None
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to absolute path for comparison
        
        Args:
            path: Path to normalize (can be relative or absolute)
            
        Returns:
            Absolute resolved path as string
        """
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = self.project_root / path_obj
        return str(path_obj.resolve())
    
    def _to_relative_path(self, path: str) -> str:
        """
        Convert path to relative path from project_root for storage
        
        Args:
            path: Path to convert (can be relative or absolute)
            
        Returns:
            Relative path from project_root as string
        """
        abs_path = Path(self._normalize_path(path))
        try:
            rel_path = abs_path.relative_to(self.project_root)
            return str(rel_path)
        except ValueError:
            # Path is outside project_root, store as absolute
            return str(abs_path)
    
    def check_duplicate_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Check if dataset name is already registered
        
        Args:
            name: Dataset name to check
            
        Returns:
            Existing mapping info if duplicate, None otherwise
        """
        mappings = self._load_dataset_mappings()
        if name in mappings['datasets']:
            return mappings['datasets'][name]
        return None
    
    def check_duplicate_path(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Check if dataset path is already registered
        
        Args:
            path: Dataset path to check (will be normalized)
            
        Returns:
            Dict with 'name' and mapping info if duplicate, None otherwise
        """
        normalized_path = self._normalize_path(path)
        mappings = self._load_dataset_mappings()
        
        for dataset_name, mapping_info in mappings['datasets'].items():
            existing_path = self._normalize_path(mapping_info['dataset_path'])
            if existing_path == normalized_path:
                return {
                    'name': dataset_name,
                    'mapping': mapping_info
                }
        return None
    
    def store_dataset_mapping(self, name: str, dvc_file_path: str, dataset_path: str):
        """
        Store mapping between user-defined name and DVC file with duplicate checking
        
        Args:
            name: Dataset name (must match folder name)
            dvc_file_path: Path to DVC file
            dataset_path: Path to dataset directory
            
        Raises:
            ValueError: If name or path is already registered, or name doesn't match folder name
        """
        # Verify name matches folder basename (consistency check)
        expected_name = Path(dataset_path).name
        if name != expected_name:
            raise ValueError(
                f"Dataset name '{name}' does not match folder name '{expected_name}'.\n"
                f"  Dataset names must match their folder names for consistency.\n"
                f"  \n"
                f"  💡 Use version aliases for custom labels:\n"
                f"     ddoc dataset commit -m 'message' -a <alias>\n"
                f"     ddoc dataset tag rename {expected_name} <version> -a <alias>"
            )
        
        # Check for duplicate name
        existing_name = self.check_duplicate_name(name)
        if existing_name:
            # Allow if it's the same path (update scenario)
            existing_path_normalized = self._normalize_path(existing_name['dataset_path'])
            current_path_normalized = self._normalize_path(dataset_path)
            
            if existing_path_normalized != current_path_normalized:
                raise ValueError(
                    f"Dataset name '{name}' is already registered at a different path.\n"
                    f"  Existing: {existing_name['dataset_path']}\n"
                    f"  New: {dataset_path}\n"
                    f"  Registered at: {existing_name.get('registered_at', 'unknown')}\n"
                    f"Cannot register the same name for different paths."
                )
        
        # Check for duplicate path
        existing_path = self.check_duplicate_path(dataset_path)
        if existing_path:
            # Ensure the name matches
            if existing_path['name'] != name:
                raise ValueError(
                    f"Dataset path '{dataset_path}' is already registered as '{existing_path['name']}'.\n"
                    f"  Path: {existing_path['mapping']['dataset_path']}\n"
                    f"  Registered at: {existing_path['mapping'].get('registered_at', 'unknown')}\n"
                    f"Cannot register the same path with different names."
                )
        
        # Store with relative path for portability
        rel_dataset_path = self._to_relative_path(dataset_path)
        rel_dvc_file_path = self._to_relative_path(dvc_file_path)
        
        mappings = self._load_dataset_mappings()
        mappings['datasets'][name] = {
            'dvc_file': rel_dvc_file_path,
            'dataset_path': rel_dataset_path,
            'registered_at': datetime.now().isoformat()
        }
        mappings['last_updated'] = datetime.now().isoformat()
        self._save_dataset_mappings(mappings)
    
    def get_dataset_mapping(self, name: str) -> Optional[Dict[str, Any]]:
        """Get dataset mapping by name"""
        mappings = self._load_dataset_mappings()
        return mappings['datasets'].get(name)
    
    def get_all_dataset_mappings(self) -> Dict[str, Any]:
        """Get all dataset mappings"""
        return self._load_dataset_mappings()
    
    def _load_lineage(self) -> Dict[str, Any]:
        """Load lineage data and build graph with mtime-based caching"""
        if self._lineage_loaded and self.lineage_file.exists():
            try:
                current_mtime = self.lineage_file.stat().st_mtime
                
                # Use cache if available and file hasn't changed
                if (self._lineage_cache is not None and 
                    self._lineage_mtime == current_mtime):
                    return self._lineage_cache
            except Exception:
                pass
        
        if self.lineage_file.exists():
            try:
                with open(self.lineage_file, 'r') as f:
                    lineage_data = json.load(f)
                    self._build_graph_from_data(lineage_data)
                    
                    # Update cache
                    self._lineage_cache = lineage_data
                    try:
                        self._lineage_mtime = self.lineage_file.stat().st_mtime
                    except Exception:
                        self._lineage_mtime = None
                    
                    self._lineage_loaded = True
                    return lineage_data
            except (json.JSONDecodeError, KeyError):
                print("Warning: Could not load lineage data, starting fresh")
                return self._init_lineage()
        
        self._lineage_loaded = True
        return self._init_lineage()
    
    def _build_graph_from_data(self, lineage_data: Dict[str, Any]):
        """Build graph from stored data"""
        # 노드 추가
        for node_data in lineage_data.get('nodes', []):
            self.graph.add_node(
                node_data['id'],
                type=node_data['type'],
                name=node_data['name'],
                timestamp=node_data['timestamp'],
                metadata=node_data.get('metadata', {})
            )
        
        # 엣지 추가
        for edge_data in lineage_data.get('edges', []):
            self.graph.add_edge(
                edge_data['source'],
                edge_data['target'],
                relationship=edge_data['relationship'],
                metadata=edge_data.get('metadata', {})
            )
    
    def _save_lineage(self, lineage: Dict[str, Any] = None):
        """Save lineage data and graph, invalidate cache"""
        if lineage is None:
            # 그래프에서 데이터 생성
            nodes = []
            edges = []
            
            # 노드 정보 수집
            for node_id, attrs in self.graph.nodes(data=True):
                nodes.append({
                    'id': node_id,
                    'type': attrs.get('type', 'unknown'),
                    'name': attrs.get('name', node_id),
                    'timestamp': attrs.get('timestamp', ''),
                    'metadata': attrs.get('metadata', {})
                })
            
            # 엣지 정보 수집
            for source, target, attrs in self.graph.edges(data=True):
                edges.append({
                    'source': source,
                    'target': target,
                    'relationship': attrs.get('relationship', 'unknown'),
                    'metadata': attrs.get('metadata', {})
                })
            
            lineage = {
                'nodes': nodes,
                'edges': edges,
                'last_updated': datetime.now().isoformat()
            }
        
        with open(self.lineage_file, 'w') as f:
            json.dump(lineage, f, indent=2)
        
        # Invalidate cache
        self._lineage_cache = None
        self._lineage_mtime = None
    
    def get_analysis_info(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific analysis
        """
        lineage = self._load_lineage()
        return lineage['analyses'].get(analysis_id)
    
    def get_experiment_info(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific experiment
        """
        lineage = self._load_lineage()
        return lineage['experiments'].get(exp_id)
    
    def list_all_datasets(self) -> List[str]:
        """
        List all datasets in lineage
        """
        lineage = self._load_lineage()
        return list(lineage['datasets'].keys())
    
    def get_version_analyses(self, dataset_name: str, dataset_version: str) -> List[Dict[str, Any]]:
        """
        Get all analyses for a specific dataset version
        """
        lineage = self._load_lineage()
        
        if dataset_name in lineage['datasets']:
            versions = lineage['datasets'][dataset_name].get('versions', {})
            if dataset_version in versions:
                return versions[dataset_version].get('analyses', [])
        
        return []
    
    def get_version_experiments(self, dataset_name: str, dataset_version: str) -> List[Dict[str, Any]]:
        """
        Get all experiments for a specific dataset version
        """
        lineage = self._load_lineage()
        
        if dataset_name in lineage['datasets']:
            versions = lineage['datasets'][dataset_name].get('versions', {})
            if dataset_version in versions:
                return versions[dataset_version].get('experiments', [])
        
        return []
    
    # =========================================================================
    # 고급 계보 추적 기능 (lineage_tracker에서 통합)
    # =========================================================================
    
    def add_dataset(self, dataset_id: str, dataset_name: str, version: str = None, metadata: Dict[str, Any] = None):
        """데이터셋 노드 추가 (버전 지원)"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        metadata = metadata or {}
        alias = metadata.get("alias")

        self.graph.add_node(
            dataset_id,
            type='dataset',
            name=dataset_name,
            version=version,
            alias=alias,
            timestamp=datetime.now().isoformat(),
            metadata=metadata
        )
        self._save_lineage()
    
    def add_analysis(self, analysis_id: str, analysis_name: str, dataset_id: str, metadata: Dict[str, Any] = None):
        """분석 노드 추가 및 관계 설정 (dataset_id는 {name}@{version} 형식)"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        self.graph.add_node(
            analysis_id,
            type='analysis',
            name=analysis_name,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        # 데이터셋과의 관계 설정
        self.graph.add_edge(
            dataset_id,  # test_ref@v1.0
            analysis_id,
            relationship='generates',
            metadata={'timestamp': datetime.now().isoformat()}
        )
        self._save_lineage()
    
    def add_experiment(self, experiment_id: str, experiment_name: str, dataset_id: str, metadata: Dict[str, Any] = None):
        """실험 노드 추가 및 관계 설정 (dataset_id는 {name}@{version} 형식)"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        self.graph.add_node(
            experiment_id,
            type='experiment',
            name=experiment_name,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        # 데이터셋과의 관계 설정
        self.graph.add_edge(
            dataset_id,  # test_ref@v1.0
            experiment_id,
            relationship='uses',
            metadata={'timestamp': datetime.now().isoformat()}
        )
        self._save_lineage()

    def update_dataset_alias(self, dataset_id: str, alias: Optional[str]) -> bool:
        """Update alias metadata for a dataset version node."""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        if dataset_id not in self.graph:
            return False

        node_attrs = self.graph.nodes[dataset_id]
        node_attrs["alias"] = alias

        metadata = node_attrs.get("metadata", {}) or {}
        if alias is None:
            metadata.pop("alias", None)
        else:
            metadata["alias"] = alias
        node_attrs["metadata"] = metadata

        self._save_lineage()
        return True

    def get_dataset_timeline(self, dataset_name: str) -> List[Dict[str, Any]]:
        """Return chronological events for a dataset across versions and analyses."""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        timeline: List[Dict[str, Any]] = []

        def _parse_timestamp(ts: Optional[str]) -> datetime:
            if not ts:
                return datetime.min
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                try:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    return datetime.min

        # Collect dataset version nodes
        dataset_nodes = [
            (node_id, attrs)
            for node_id, attrs in self.graph.nodes(data=True)
            if attrs.get('type') == 'dataset' and attrs.get('name') == dataset_name
        ]

        if not dataset_nodes:
            return []

        for node_id, attrs in dataset_nodes:
            dataset_event = {
                'event_type': 'version',
                'dataset': dataset_name,
                'dataset_id': node_id,
                'version': attrs.get('version'),
                'alias': attrs.get('alias') or attrs.get('metadata', {}).get('alias'),
                'timestamp': attrs.get('timestamp'),
                'metadata': attrs.get('metadata', {})
            }
            timeline.append(dataset_event)

            for neighbor in self.graph.successors(node_id):
                neighbor_attrs = self.graph.nodes[neighbor]
                edge_attrs = self.graph.edges[node_id, neighbor]
                event = {
                    'event_type': neighbor_attrs.get('type', 'unknown'),
                    'dataset': dataset_name,
                    'dataset_id': node_id,
                    'dataset_version': attrs.get('version'),
                    'alias': attrs.get('alias') or attrs.get('metadata', {}).get('alias'),
                    'id': neighbor,
                    'name': neighbor_attrs.get('name', neighbor),
                    'timestamp': neighbor_attrs.get('timestamp'),
                    'relationship': edge_attrs.get('relationship'),
                    'metadata': neighbor_attrs.get('metadata', {})
                }
                timeline.append(event)

        timeline.sort(key=lambda ev: (_parse_timestamp(ev.get('timestamp')), 0 if ev.get('event_type') == 'version' else 1))
        return timeline
    
    def add_drift_analysis(self, drift_id: str, drift_name: str, ref_dataset: str, cur_dataset: str, metadata: Dict[str, Any] = None):
        """드리프트 분석 노드 추가"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        self.graph.add_node(
            drift_id,
            type='drift_analysis',
            name=drift_name,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        # 참조 데이터셋과의 관계
        self.graph.add_edge(
            ref_dataset,
            drift_id,
            relationship='baseline',
            metadata={'timestamp': datetime.now().isoformat()}
        )
        # 현재 데이터셋과의 관계
        self.graph.add_edge(
            cur_dataset,
            drift_id,
            relationship='target',
            metadata={'timestamp': datetime.now().isoformat()}
        )
        self._save_lineage()
    
    def get_lineage(self, node_id: str, depth: int = 2) -> Dict[str, Any]:
        """특정 노드의 계보 정보 조회"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        if node_id not in self.graph:
            return {"error": f"Node {node_id} not found"}
        
        # BFS로 깊이 제한된 계보 탐색
        visited = set()
        queue = [(node_id, 0)]
        lineage_nodes = []
        lineage_edges = []
        
        while queue:
            current_node, current_depth = queue.pop(0)
            if current_node in visited or current_depth > depth:
                continue
            
            visited.add(current_node)
            node_attrs = self.graph.nodes[current_node]
            lineage_nodes.append({
                'id': current_node,
                'type': node_attrs.get('type', 'unknown'),
                'name': node_attrs.get('name', current_node),
                'timestamp': node_attrs.get('timestamp', ''),
                'metadata': node_attrs.get('metadata', {})
            })
            
            # 인접 노드들 추가
            for neighbor in self.graph.neighbors(current_node):
                if neighbor not in visited:
                    queue.append((neighbor, current_depth + 1))
                    edge_attrs = self.graph.edges[current_node, neighbor]
                    lineage_edges.append({
                        'source': current_node,
                        'target': neighbor,
                        'relationship': edge_attrs.get('relationship', 'unknown'),
                        'metadata': edge_attrs.get('metadata', {})
                    })
        
        return {
            'root_node': node_id,
            'nodes': lineage_nodes,
            'edges': lineage_edges,
            'total_nodes': len(lineage_nodes),
            'total_edges': len(lineage_edges),
            'depth': depth,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_full_lineage(self) -> Dict[str, Any]:
        """전체 계보 정보 조회"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        nodes = []
        edges = []
        
        for node_id, attrs in self.graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'type': attrs.get('type', 'unknown'),
                'name': attrs.get('name', node_id),
                'timestamp': attrs.get('timestamp', ''),
                'metadata': attrs.get('metadata', {})
            })
        
        for source, target, attrs in self.graph.edges(data=True):
            edges.append({
                'source': source,
                'target': target,
                'relationship': attrs.get('relationship', 'unknown'),
                'metadata': attrs.get('metadata', {})
            })
        
        # 노드 타입과 관계 타입 수집
        node_types = set()
        relationship_types = set()
        
        for node in nodes:
            node_types.add(node['type'])
        
        for edge in edges:
            relationship_types.add(edge['relationship'])
        
        return {
            'nodes': nodes,
            'edges': edges,
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'node_types': list(node_types),
            'relationship_types': list(relationship_types),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_dependencies(self, node_id: str) -> List[str]:
        """특정 노드의 의존성 조회"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        if node_id not in self.graph:
            return []
        return list(self.graph.predecessors(node_id))
    
    def get_dependents(self, node_id: str) -> List[str]:
        """특정 노드에 의존하는 노드들 조회"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        if node_id not in self.graph:
            return []
        return list(self.graph.successors(node_id))
    
    def get_impact_analysis(self, node_id: str) -> Dict[str, Any]:
        """노드 변경의 영향 분석"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        if node_id not in self.graph:
            return {"error": f"Node {node_id} not found"}
        
        # 직접 의존성
        direct_deps = self.get_dependencies(node_id)
        # 간접 의존성 (재귀적)
        indirect_deps = set()
        for dep in direct_deps:
            indirect_deps.update(self.get_dependencies(dep))
        
        # 직접 의존자
        direct_dependents = self.get_dependents(node_id)
        # 간접 의존자 (재귀적)
        indirect_dependents = set()
        for dep in direct_dependents:
            indirect_dependents.update(self.get_dependents(dep))
        
        # 모든 의존자 (직접 + 간접)
        all_dependents = list(direct_dependents) + list(indirect_dependents)
        impact_count = len(all_dependents)
        
        # 영향도 심각도 계산
        if impact_count >= 5:
            impact_severity = 'high'
        elif impact_count >= 2:
            impact_severity = 'medium'
        else:
            impact_severity = 'low'
        
        return {
            'node_id': node_id,
            'direct_dependencies': direct_deps,
            'indirect_dependencies': list(indirect_deps),
            'direct_dependents': direct_dependents,
            'indirect_dependents': list(indirect_dependents),
            'all_dependents': all_dependents,
            'impact_count': impact_count,
            'impact_severity': impact_severity,
            'impact_score': len(direct_dependents) + len(indirect_dependents),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_lineage_overview(self) -> Dict[str, Any]:
        """전체 계보 개요 정보 조회 (트리 구조용)"""
        # Lazy load lineage if not loaded yet
        if not self._lineage_loaded:
            self._load_lineage()
        
        # 노드 타입별로 그룹화
        datasets = []
        analyses = []
        experiments = []
        drift_analyses = []
        
        # 노드들을 타입별로 분류
        for node_id, attrs in self.graph.nodes(data=True):
            node_type = attrs.get('type', 'unknown')
            node_info = {
                'id': node_id,
                'name': attrs.get('name', node_id),
                'timestamp': attrs.get('timestamp', ''),
                'version': attrs.get('version', ''),
                'metadata': attrs.get('metadata', {})
            }
            
            if node_type == 'dataset':
                datasets.append(node_info)
            elif node_type == 'analysis':
                analyses.append(node_info)
            elif node_type == 'experiment':
                experiments.append(node_info)
            elif node_type == 'drift_analysis':
                drift_analyses.append(node_info)
        
        # 관계 정보 수집
        relationships = []
        for source, target, attrs in self.graph.edges(data=True):
            relationships.append({
                'source': source,
                'target': target,
                'relationship': attrs.get('relationship', 'unknown'),
                'timestamp': attrs.get('metadata', {}).get('timestamp', '')
            })
        
        # 데이터셋별 하위 노드들 매핑
        dataset_children = {}
        for dataset in datasets:
            dataset_id = dataset['id']
            dataset_children[dataset_id] = {
                'analyses': [],
                'experiments': [],
                'drift_analyses': []
            }
            
            # 해당 데이터셋과 연결된 노드들 찾기
            for rel in relationships:
                if rel['source'] == dataset_id:
                    target_id = rel['target']
                    target_type = rel['relationship']
                    
                    # 타겟 노드 정보 찾기
                    target_info = None
                    if target_type == 'generates':
                        target_info = next((a for a in analyses if a['id'] == target_id), None)
                        if target_info:
                            dataset_children[dataset_id]['analyses'].append(target_info)
                    elif target_type == 'uses':
                        target_info = next((e for e in experiments if e['id'] == target_id), None)
                        if target_info:
                            dataset_children[dataset_id]['experiments'].append(target_info)
                    elif target_type in ['baseline', 'target']:
                        target_info = next((d for d in drift_analyses if d['id'] == target_id), None)
                        if target_info:
                            dataset_children[dataset_id]['drift_analyses'].append(target_info)
        
        return {
            'datasets': datasets,
            'analyses': analyses,
            'experiments': experiments,
            'drift_analyses': drift_analyses,
            'relationships': relationships,
            'dataset_children': dataset_children,
            'total_nodes': len(self.graph.nodes),
            'total_edges': len(self.graph.edges),
            'timestamp': datetime.now().isoformat()
        }
    
    def export_graph(self, format: str = 'json') -> Dict[str, Any]:
        """그래프를 다양한 형식으로 내보내기"""
        if format == 'json':
            return self.get_full_lineage()
        elif format == 'dot':
            return self._generate_dot_format()
        else:
            return {"error": f"Unsupported format: {format}"}
    
    def _generate_dot_format(self) -> str:
        """DOT 형식으로 그래프 생성"""
        dot_lines = ["digraph lineage {"]
        dot_lines.append("  rankdir=TB;")
        dot_lines.append("  node [shape=box];")
        
        # 노드 추가
        for node_id, attrs in self.graph.nodes(data=True):
            node_type = attrs.get('type', 'unknown')
            node_name = attrs.get('name', node_id)
            color = {
                'dataset': 'lightblue',
                'analysis': 'lightgreen', 
                'experiment': 'lightyellow',
                'drift_analysis': 'lightcoral'
            }.get(node_type, 'lightgray')
            
            dot_lines.append(f'  "{node_id}" [label="{node_name}", fillcolor="{color}", style="filled"];')
        
        # 엣지 추가
        for source, target, attrs in self.graph.edges(data=True):
            relationship = attrs.get('relationship', 'unknown')
            color = {
                'uses': 'blue',
                'generates': 'green',
                'baseline': 'red',
                'target': 'orange'
            }.get(relationship, 'black')
            
            dot_lines.append(f'  "{source}" -> "{target}" [label="{relationship}", color="{color}"];')
        
        dot_lines.append("}")
        return "\n".join(dot_lines)


# Global metadata service instance
_metadata_service = None


def get_metadata_service(project_root: str = ".") -> MetadataService:
    """Get global metadata service instance"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService(project_root)
    return _metadata_service
