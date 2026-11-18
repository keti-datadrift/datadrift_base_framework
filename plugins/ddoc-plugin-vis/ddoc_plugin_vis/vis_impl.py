from importlib.resources import files
import subprocess
import pluggy

hookimpl = pluggy.HookimplMarker("ddoc")

class DDOCVisPlugin:
    @hookimpl
    def vis_run(self):
        app_path = files("ddoc_plugin_vis") / "app.py"
        subprocess.Popen(["streamlit", "run", str(app_path)])
        return [{"name": "ddoc_vis", "type": "streamlit", "app_path": str(app_path)}]

         