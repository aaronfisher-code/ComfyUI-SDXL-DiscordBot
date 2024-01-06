import configparser
import json
import logging
import urllib
import uuid
from collections import defaultdict
from io import BytesIO

import requests
import websockets
from PIL import Image


async def refresh_models():
    global models
    global loras
    models = get_models()
    loras = get_loras()
    logger.info("refreshed models.")


def queue_prompt(prompt, client_id):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()


def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())


def clear_history():
    p = {"clear": True}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request("http://{}/history".format(server_address), data=data)
    response = urllib.request.urlopen(req).read()


def upload_image(filepath, subfolder=None, folder_type=None, overwrite=False):
    url = f"http://{server_address}/upload/image"
    files = {"image": open(filepath, "rb")}
    data = {"overwrite": str(overwrite).lower()}
    if subfolder:
        data["subfolder"] = subfolder
    if folder_type:
        data["type"] = folder_type
    response = requests.post(url, files=files, data=data)
    return response.json()


def get_node_input_choices(node_name, input_name):
    logger.debug('fetching possible values for input "%s" of node "%s"', input_name, node_name)
    with urllib.request.urlopen("http://{}/object_info".format(server_address)) as response:
        object_info = json.loads(response.read())
        return object_info[node_name]["input"]["required"][input_name]


def get_models():
    return get_node_input_choices("CheckpointLoaderSimple", "ckpt_name")


def get_loras():
    return get_node_input_choices("LoraLoader", "lora_name")


def get_samplers():
    return get_node_input_choices("KSampler", "sampler_name")


def get_tortoise_voices():
    return get_node_input_choices("TortoiseTTSGenerate", "voice")


class ComfyGenerator:
    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self.uri = f"ws://{server_address}/ws?clientId={self.client_id}"
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.uri)

    async def get_images(self, prompt):
        if not self.ws:
            await self.connect()

        prompt_id = queue_prompt(prompt, self.client_id)["prompt_id"]
        currently_executing_Prompt = None
        full_prompt = None
        async for out in self.ws:
            try:
                message = json.loads(out)
                if message["type"] == "execution_start":
                    currently_executing_Prompt = message["data"]["prompt_id"]
                if message["type"] == "executing" and prompt_id == currently_executing_Prompt:
                    data = message["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break
            except ValueError as e:
                logger.warning("Incompatible response from ComfyUI")

        history = get_history(prompt_id)[prompt_id]

        output = defaultdict(list)

        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "text" in node_output:
                for prompt in node_output["text"]:
                    full_prompt = prompt
            if "images" in node_output:
                for image in node_output["images"]:
                    image_data = get_image(image["filename"], image["subfolder"], image["type"])
                    if "final_output" in image["filename"]:
                        pil_image = Image.open(BytesIO(image_data))
                        output["images"].append(pil_image)
            if "gifs" in node_output:
                for gif in node_output["gifs"]:
                    image_data = get_image(gif["filename"], gif["subfolder"], gif["type"])
                    if "final_output" in gif["filename"]:
                        pil_image = Image.open(BytesIO(image_data))
                        output["gifs"].append(pil_image)
            if "clips" in node_output:
                for clip in node_output["clips"]:
                    data = get_image(clip["filename"], clip["subfolder"], clip["type"])
                    if "final_output" in clip["filename"]:
                        output["clips"].append((data, clip["filename"]))
            if "videos" in node_output:
                for video in node_output["videos"]:
                    data = get_image(video["filename"], video["subfolder"], video["type"])
                    if "final_output" in video["filename"]:
                        output["videos"].append((data, video["filename"]))

        logger.debug("Collected %d outputs", len(output))

        return output, full_prompt

    async def close(self):
        if self.ws:
            await self.ws.close()


logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.properties")
server_address = config["LOCAL"]["SERVER_ADDRESS"]

models = get_models()
loras = get_loras()
samplers = get_samplers()
