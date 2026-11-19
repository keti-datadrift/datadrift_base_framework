import pluggy
import sys

hookspec = pluggy.HookspecMarker("test")
hookimpl = pluggy.HookimplMarker("test")

# Module containing hookspecs
current_module = sys.modules[__name__]

# Module-level hookspec - NO DEFAULT VALUES
@hookspec
def my_hook(a, b, c):
    """Test hook"""

class Plugin:
    @hookimpl
    def my_hook(self, a, b, c):
        print(f"Plugin received: a={a}, b={b}, c={c}")
        return {"a": a, "b": b, "c": c}

# Test
pm = pluggy.PluginManager("test")
pm.add_hookspecs(current_module)  # Pass module, not function
pm.register(Plugin())

print("Calling with all args:")
result = pm.hook.my_hook(a="A", b="B", c="C")
print(f"Result: {result}")

