import os.path

from src import comfy_client, discord_client

if __name__ == "__main__":
    if os.path.exists("embedded_comfy"):
        comfy_client.run_comfy_client()
    discord_client.start_bot()
