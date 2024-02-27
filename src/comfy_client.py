import os
import subprocess


def run_comfy_client():
    comfy_path = "embedded_comfy"
    subprocess.Popen(["comfyui", "--port", "8188", "--listen", "localhost", "--verbose", f"--cwd={os.path.join(os.getcwd(), comfy_path)}"])
