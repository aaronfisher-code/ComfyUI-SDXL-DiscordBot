import os
import subprocess


def run_comfy_client():
    comfy_path = "embedded_comfy"
    subprocess.Popen(["python", "main.py", "--port", "8188", "--listen"], cwd=comfy_path)
