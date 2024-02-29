import configparser
import subprocess


def run_comfy_client():
    config = configparser.ConfigParser()
    config.read("config.properties")

    if config["BOT"]["USE_EMBEDDED_COMFY"].lower() == "true":
        print("Starting embedded comfy")
        comfy_path = "embedded_comfy"
        subprocess.Popen(["python", "main.py", "--port", "8188", "--listen"], cwd=comfy_path)
    else:
        print(f"Using external comfy server. Make sure it's running. Address: {config['LOCAL']['SERVER_ADDRESS']}")
