"""
Plugin manager for dd using pluggy + entry point discovery.
"""
from __future__ import annotations
import importlib
import importlib.metadata as md
import pluggy
from typing import Iterable, Optional
from dd.plugins.hookspecs import HookSpecs
from dd.core.logging import get_logger

log = get_logger(__name__)

GROUP = "dd.plugins"

class PluginManager:
    def __init__(self) -> None:
        self.pm = pluggy.PluginManager("dd")
        self.pm.add_hookspecs(HookSpecs)

    def register_builtin(self) -> None:
        # Import and register first-party builtin implementations
        try:
            mod = importlib.import_module("dd.builtin_plugins.builtin_impls")
            self.pm.register(mod, name="dd_builtins")
            log.debug("Registered built-in plugins: dd_builtins")
        except Exception as e:
            log.exception("Failed to register builtins: %s", e)

    def load_entrypoints(self, group: str = GROUP) -> None:
        # Discover external plugins via entry points
        try:
            for ep in md.entry_points(group=group):
                try:
                    plugin = ep.load()
                    # If entry point exposes a module, register it directly; if it exposes a function, call it.
                    if callable(plugin):
                        plugin(self.pm)
                        log.debug("Loaded plugin callable from entry-point: %s", ep.name)
                    else:
                        self.pm.register(plugin, name=ep.name)
                        log.debug("Registered plugin module from entry-point: %s", ep.name)
                except Exception as err:
                    log.exception("Failed to load entry-point %s: %s", ep.name, err)
        except Exception as e:
            log.debug("No entry points found or error while scanning: %s", e)

    def get_plugins(self) -> Iterable[object]:
        return self.pm.get_plugins()

def get_plugin_manager() -> PluginManager:
    pm = PluginManager()
    pm.register_builtin()
    pm.load_entrypoints()
    return pm