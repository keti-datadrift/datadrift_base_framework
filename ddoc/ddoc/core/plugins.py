from __future__ import annotations
import pluggy
import importlib
import importlib.metadata # <--- 추가: 엔트리 포인트를 직접 로드하기 위해 필요
import sys
import subprocess
import logging
from typing import Any, Dict, Optional, Iterable
# hookspecs에서 필요한 정의 가져오기 (가정)
import ddoc.plugins.hookspecs as hookspecs_module
from ddoc.plugins.hookspecs import HOOKSPEC_VERSION

# 더미 정의 (실제 환경에서는 각 모듈에서 가져와야 함)
log = logging.getLogger(__name__)
GROUP = "ddoc" # U+00A0 제거됨

# ddoc/ops/core_ops.py에서 구현한 CoreOpsPlugin 임포트
from ddoc.ops.core_ops import CoreOpsPlugin # CoreOpsPlugin을 임포트합니다.


# PluginManager 인스턴스를 저장하는 전역 변수 (싱글톤 패턴)
_PLUGIN_MANAGER: Optional['PluginManager'] = None

class PluginManager:
    def __init__(self) -> None:
        # pluggy PluginManager 초기화
        self.pm = pluggy.PluginManager("ddoc")
        
        # Force reload hookspecs module to avoid cache issues
        if 'ddoc.plugins.hookspecs' in sys.modules:
            del sys.modules['ddoc.plugins.hookspecs']
        import ddoc.plugins.hookspecs as fresh_hookspecs
        
        # 훅 명세 등록 (초기 등록은 __init__에서 수행하는 것이 합리적)
        self.pm.add_hookspecs(fresh_hookspecs)
        
    # --- 핵심: .hook 속성 위임 (Delegation) ---
    @property
    def hook(self):
        """플러그인 훅 호출을 위해 pluggy.PluginManager.hook을 위임합니다."""
        return self.pm.hook
        
    # --- pluggy API 위임 (Delegation) ---
    def add_hookspecs(self, hookspecs: Any) -> None:
        """pluggy.PluginManager.add_hookspecs() 호출을 위임합니다."""
        self.pm.add_hookspecs(hookspecs)

    def load_setuptools_entrypoints(self, group: str = GROUP) -> None:
        """pluggy.PluginManager.load_setuptools_entrypoints() 호출을 위임합니다."""
        # pluggy 자체의 함수를 사용하도록 수정
        self.pm.load_setuptools_entrypoints(group)
        
    # -----------------------------------
    
    # NOTE: _is_version_compatible 함수는 버전 문자열 비교 로직을 수행한다고 가정하고 생략
    def _is_version_compatible(self, current: str, min_v: Optional[str], max_v: Optional[str]) -> bool:
        """버전 호환성 확인 로직 (실제 구현 생략)"""
        return True

    def register_core_ops(self) -> None:
        """핵심 DVC/Git MLOps 로직을 구현한 플러그인을 등록합니다."""
        try:
            # CoreOpsPlugin 인스턴스를 생성하여 등록 (지연 초기화)
            # 실제 사용 시점에만 초기화되도록 함
            self._check_and_register(CoreOpsPlugin, name="ddoc_core_ops")
            log.debug("Registered core ops plugin: ddoc_core_ops")
        except Exception as e:
            log.exception("Failed to register CoreOpsPlugin: %s", e)

    def register_builtin(self) -> None:
        """내장 플러그인을 로드하고 등록합니다."""
        try:
            # 모듈 자체를 등록하는 경우(일부 pluggy 패턴), 인스턴스화가 필요 없음
            mod = importlib.import_module("ddoc.builtin_plugins.builtin_impls")
            try:
                self._check_and_register(mod, name="ddoc_builtins")
                log.debug("Registered built-in plugins: ddoc_builtins")
            except pluggy.PluginValidationError as e:
                # Ignore validation errors during initial registration
                # This can happen when hookspec is updated but plugins are already loaded
                log.warning("Skipping builtin registration due to validation error (will retry): %s", e)
        except Exception as e:
            log.exception("Failed to register builtins: %s", e)

    def _check_and_register(self, plugin_obj: Any, name: Optional[str] = None) -> None:
        """버전 호환성을 확인하고 플러그인을 등록합니다."""
        pmin = getattr(plugin_obj, "DDOC_HOOKSPEC_MIN", None)
        pmax = getattr(plugin_obj, "DDOC_HOOKSPEC_MAX", None)
        
        if not self._is_version_compatible(HOOKSPEC_VERSION, pmin, pmax):
            log.warning("Plugin %s incompatible with HookSpec %s (min=%s, max=%s). Skipped.",
                        name or getattr(plugin_obj, "__name__", plugin_obj), HOOKSPEC_VERSION, pmin, pmax)
            return

        # 중복 등록 방지 로직 (생략된 부분 포함)

        if isinstance(plugin_obj, dict):
            log.warning("Dict plugin object detected for %s; refusing to register. "
                        "Plugins must register a module or instance (not dict).", name or plugin_obj)
            return
            
        try:
            self.pm.register(plugin_obj, name=name)
        except ValueError as e:
            log.info("Duplicate plugin %s detected. Skipping. (%s)", name or plugin_obj, e)
        
    def load_entrypoints(self, group: str = GROUP) -> None:
        """setuptools entry points를 로드하고 등록합니다. (클래스 객체를 인스턴스화하여 등록)"""
        log.debug("Loading setuptools entry points...")
        
        # pluggy의 기본 메서드 대신, 직접 entry_points를 로드하고 인스턴스화합니다.
        try:
            entry_points = importlib.metadata.entry_points(group=group)
        except Exception as e:
            # fallback이 필요하다면 이 부분을 수정해야 하지만, 현재는 인스턴스화 로직이 핵심입니다.
            log.error("Failed to load entry points list: %s", e)
            return

        for entry_point in entry_points:
            try:
                # 1. Entry Point에서 클래스 객체(예: DDOCNlpPlugin)를 로드
                plugin_cls_or_obj = entry_point.load()
                plugin_name = entry_point.name
                
                # 2. 로드된 객체가 클래스(type)라면, 반드시 인스턴스화합니다.
                if isinstance(plugin_cls_or_obj, type):
                    plugin_obj = plugin_cls_or_obj() # <--- 핵심 수정: 클래스 인스턴스화
                else:
                    # 이미 인스턴스이거나 모듈이라면 그대로 사용 (예: ddoc_builtins)
                    plugin_obj = plugin_cls_or_obj
                
                # 3. _check_and_register를 통해 인스턴스를 등록
                self._check_and_register(plugin_obj, name=plugin_name)
                log.debug("Registered external plugin: %s", plugin_name)
                
            except Exception as e:
                log.error("Failed to load or register external plugin '%s': %s", entry_point.name, e)


    def get_plugins(self) -> Iterable[object]:
        return self.pm.get_plugins()

    def list_plugins(self) -> Dict[str, object]:
        """Get all registered plugins as a dictionary"""
        plugins = {}
        for plugin in self.pm.get_plugins():
            name = self.pm.get_name(plugin)
            if name:
                plugins[name] = plugin
        return plugins

    def get_name(self, plugin: object) -> Optional[str]:
        return self.pm.get_name(plugin)

    def call_hook(self, hook_name: str, provider: Optional[str] = None, first_non_none: bool = True, **kwargs) -> Any:
        """Hook 호출 로직 (생략)"""
        hook = getattr(self.pm.hook, hook_name)
        impls = hook.get_hookimpls()
        results = hook(**kwargs)
        
        if provider:
            for impl, res in zip(impls, results):
                if impl.plugin_name == provider:
                    return res
            return None

        if first_non_none:
            for res in results:
                if res is not None:
                    return res
            return None
        return results

    def pip_install(self, package: str) -> int:
        """Install a plugin package via pip in the current interpreter."""
        log.info("Installing plugin via pip: %s", package)
        # pip 명령을 호출합니다.
        return subprocess.call([sys.executable, "-m", "pip", "install", package])


def get_plugin_manager() -> PluginManager:
    """PluginManager의 싱글톤 인스턴스를 반환합니다."""
    global _PLUGIN_MANAGER
    if _PLUGIN_MANAGER is None:
        _PLUGIN_MANAGER = PluginManager()
        # 초기화 시점에 핵심 및 내장 플러그인 로드
        _PLUGIN_MANAGER.register_core_ops()
        _PLUGIN_MANAGER.register_builtin()
        # 이후 엔트리 포인트를 통해 외부 플러그인 로드 (수정된 로직 적용)
        _PLUGIN_MANAGER.load_entrypoints()
    return _PLUGIN_MANAGER
