from __future__ import annotations
import typer
import json
from rich import print
from rich.console import Console
from typing import Optional, Dict, Any, List
from ddoc.core.plugins import get_plugin_manager
from ddoc.plugins.hookspecs import HOOKSPEC_VERSION # HOOKSPEC_VERSION 임포트 가정

app = typer.Typer(help="Plugin management")
console = Console()

def get_all_hook_names(pm: Any) -> List[str]:
    """PluginManager에서 동적으로 등록된 모든 훅 이름을 가져옵니다."""
    return [
        name 
        for name in dir(pm.hook) 
        if not name.startswith("_") and name not in ["list_hookcallers", "call_historic"]
    ]

@app.command("list")
def plugin_list():
    """로드된 플러그인과 구현된 훅 목록을 표시."""
    pm = get_plugin_manager()
    rows = []
    
    all_hook_names = get_all_hook_names(pm)
    
    for plugin in pm.get_plugins():
        name = pm.get_name(plugin) or str(plugin)
        impls: List[str] = []
        
        for hook_name in all_hook_names:
            caller = getattr(pm.hook, hook_name, None)
            if caller is None:
                continue
                
            implements = any(hi.plugin is plugin for hi in caller.get_hookimpls())
            
            if implements:
                impls.append(hook_name)
                
        rows.append({"name": name, "implements": impls})
        
    print({"hookspec_version": HOOKSPEC_VERSION, "plugins": rows})

# ----------------------------------------------------------------------
@app.command("info")
def plugin_info(name: str):
    """이름으로 특정 플러그인의 상세 정보를 표시."""
    pm = get_plugin_manager()
    all_hook_names = get_all_hook_names(pm)
    
    for plugin in pm.get_plugins():
        pname = pm.get_name(plugin)
        if pname == name:
            info = {
                "name": pname,
                "module": getattr(plugin, "__name__", str(plugin)),
                "hookspec_min": getattr(plugin, "DDOC_HOOKSPEC_MIN", "N/A"),
                "hookspec_max": getattr(plugin, "DDOC_HOOKSPEC_MAX", "N/A"),
                "implements": [],
            }
            
            for hook_name in all_hook_names:
                caller = getattr(pm.hook, hook_name, None)
                if caller and any(hi.plugin is plugin for hi in caller.get_hookimpls()):
                    info["implements"].append(hook_name)
                    
            print(info)
            return
            
    print({"error": f"Plugin not found: {name}"})

# ----------------------------------------------------------------------
@app.command("install")
def plugin_install(package: str):
    """pip를 통해 플러그인 패키지를 설치하고 엔트리 포인트를 다시 로드."""
    
    # 🌟 수정된 부분: get_plugin_manager()에서 반환된 객체(PluginManager)를 직접 사용합니다.
    pmgr = get_plugin_manager()
    
    # PluginManager 인스턴스에 정의된 pip_install 메서드를 호출합니다.
    code = pmgr.pip_install(package)
    
    if code == 0:
        # 새로 설치된 플러그인을 감지하기 위해 엔트리 포인트를 다시 로드합니다.
        pmgr.load_entrypoints() 
        console.print(f"[bold green]✅ Success:[/bold green] Plugin '{package}' installed and loaded.")
        print({"ok": True, "installed": package})
    else:
        console.print(f"[bold red]❌ Error:[/bold red] Failed to install plugin '{package}'. See pip output above.")
        print({"ok": False, "installed": package, "code": code})
