import configparser
import json
import requests
import tempfile
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import websockets
from PIL import Image


@dataclass
class ImageWorkflow:
    workflow_name: str

    prompt: str
    negative_prompt: Optional[str] = None

    model: Optional[str] = None
    loras: Optional[list[str]] = None
    lora_strengths: Optional[list[float]] = None

    aspect_ratio: Optional[str] = None
    sampler: Optional[str] = None
    num_steps: Optional[int] = None
    cfg_scale: Optional[float] = None

    denoise_strength: Optional[float] = None

    seed: Optional[int] = None
    filename: str = None


# Read the configuration
config = configparser.ConfigParser()
config.read("config.properties")
server_address = config["LOCAL"]["SERVER_ADDRESS"]


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
    p = {
        'clear': True
    }
    data = json.dumps(p).encode('utf-8')
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


def get_models():
    with urllib.request.urlopen("http://{}/object_info".format(server_address)) as response:
        object_info = json.loads(response.read())
        return object_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"]



def get_loras():
    with urllib.request.urlopen("http://{}/object_info".format(server_address)) as response:
        object_info = json.loads(response.read())
        return object_info["LoraLoader"]["input"]["required"]["lora_name"]


def get_samplers():
    with urllib.request.urlopen("http://{}/object_info".format(server_address)) as response:
        object_info = json.loads(response.read())
        return object_info["KSampler"]["input"]["required"]["sampler_name"]



class ImageGenerator:
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
        output_images = []
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
                print("Incompatible response from ComfyUI")

        history = get_history(prompt_id)[prompt_id]

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
                        output_images.append(pil_image)

        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "gifs" in node_output:
                for gif in node_output["gifs"]:
                    image_data = get_image(gif["filename"], gif["subfolder"], gif["type"])
                    if "final_output" in gif["filename"]:
                        pil_image = Image.open(BytesIO(image_data))
                        output_images.append(pil_image)

        return output_images, full_prompt

    async def close(self):
        if self.ws:
            await self.ws.close()


def setup_workflow(workflow, params: ImageWorkflow):
    prompt_nodes = config.get(params.workflow_name, "PROMPT_NODES").split(",")
    neg_prompt_nodes = config.get(params.workflow_name, "NEG_PROMPT_NODES").split(",")
    rand_seed_nodes = config.get(params.workflow_name, "RAND_SEED_NODES").split(",")
    model_node = config.get(params.workflow_name, "MODEL_NODE").split(",")
    lora_node = config.get(params.workflow_name, "LORA_NODE").split(",")
    llm_model_node = None

    if config.has_option(params.workflow_name, "FILE_INPUT_NODES"):
        file_input_nodes = config.get(params.workflow_name, "FILE_INPUT_NODES").split(",")

    if config.has_option(params.workflow_name, "LLM_MODEL_NODE"):
        llm_model_node = config.get(params.workflow_name, "LLM_MODEL_NODE")

    # Modify the prompt dictionary
    if params.prompt is not None and prompt_nodes[0] != "":
        for node in prompt_nodes:
            if "text" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["text"] = params.prompt
            elif "prompt" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["prompt"] = params.prompt

    if params.negative_prompt is not None and neg_prompt_nodes[0] != "":
        for node in neg_prompt_nodes:
            workflow[node]["inputs"]["text"] = params.negative_prompt + ", (children, child, kids, kid:1.3)"

    if params.filename is not None and config.has_option(
        params.workflow_name, "FILE_INPUT_NODES"
    ):
        for node in file_input_nodes:
            workflow[node]["inputs"]["image"] = params.filename

    if rand_seed_nodes[0] != "":
        for node in rand_seed_nodes:
            workflow[node]["inputs"]["seed"] = params.seed

    if params.model is not None and model_node[0] != "":
        for node in model_node:
            if "ckpt_name" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["ckpt_name"] = params.model
            elif "base_ckpt_name" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["base_ckpt_name"] = params.model

    if params.loras is not None and lora_node[0] != "":
        lora_strengths = params.lora_strengths or [1.0] * len(params.loras)
        for i, lora in enumerate(params.loras):
            if lora is None:
                continue
            for node in lora_node:
                istr = str(i + 1)
                if "lora_name_" + istr in workflow[node]["inputs"]:
                    workflow[node]["inputs"]["switch_" + istr] = "On"
                    workflow[node]["inputs"]["lora_name_" + istr] = lora
                    workflow[node]["inputs"]["model_weight_" + istr] = lora_strengths[i]
                    workflow[node]["inputs"]["clip_weight_" + istr] = lora_strengths[i]
                elif "lora_0" + istr in workflow[node]["inputs"]:
                    workflow[node]["inputs"]["lora_0" + istr] = lora
                    workflow[node]["inputs"]["strength_0" + istr] = lora_strengths[i]

    if llm_model_node is not None:
        workflow[llm_model_node]["inputs"]["model_dir"] = config["LOCAL"]["LLM_MODEL_LOCATION"]

    if params.aspect_ratio is not None:
        empty_image_node = config.get(params.workflow_name, "EMPTY_IMAGE_NODE").split(",")
        for node in empty_image_node:
            if "dimensions" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["dimensions"] = params.aspect_ratio
            else:
                w = int(params.aspect_ratio.lstrip().split("x")[0])
                h = int(params.aspect_ratio.split("x")[1].lstrip().split(" ")[0])
                workflow[node]["inputs"]["empty_latent_width"] = w
                workflow[node]["inputs"]["empty_latent_height"] = h

    # maybe set sampler arguments
    sampler_args_given = (
        params.denoise_strength is not None
        or params.sampler is not None
        or params.num_steps is not None
        or params.cfg_scale is not None
    )
    if sampler_args_given and config.has_option(params.workflow_name, "DENOISE_NODE"):
        denoise_node = config.get(params.workflow_name, "DENOISE_NODE").split(",")
        for node in denoise_node:
            default_args = workflow[node]["inputs"]
            steps = params.num_steps or default_args["steps"]
            cfg = params.cfg_scale or default_args["cfg"]
            sampler = params.sampler or default_args["sampler_name"]
            workflow[node]["inputs"]["steps"] = steps
            workflow[node]["inputs"]["cfg"] = cfg
            workflow[node]["inputs"]["sampler_name"] = sampler
            # workaround for samplers that don't have a denoise input
            if "denoise" in default_args:
                denoise = params.denoise_strength or default_args["denoise"]
                workflow[node]["inputs"]["denoise"] = denoise

    # limit batch size to 1 if denoise strength is given ()
    if params.denoise_strength is not None and config.has_option(params.workflow_name, "LATENT_IMAGE_NODE"):
        latent_image_node = config.get(params.workflow_name, "LATENT_IMAGE_NODE").split(",")
        for node in latent_image_node:
            workflow[node]["inputs"]["amount"] = 1

    return workflow


async def generate_images(params: ImageWorkflow):
    print("queuing workflow:", params)
    with open(config[params.workflow_name]["CONFIG"], "r") as file:
        workflow = json.load(file)

    generator = ImageGenerator()
    await generator.connect()

    setup_workflow(workflow, params)

    images, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    return images, enhanced_prompt


async def generate_alternatives(params: ImageWorkflow, image: Image.Image):
    print("queuing workflow:", params)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
        image.save(temp_file, format="PNG")
        temp_filepath = temp_file.name

    # Upload the temporary file using the upload_image method
    response_data = upload_image(temp_filepath)
    filename = response_data["name"]
    params.filename = filename

    with open(config[params.workflow_name]["CONFIG"], "r") as file:
        workflow = json.load(file)

    generator = ImageGenerator()
    await generator.connect()

    setup_workflow(workflow, params)

    images, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    return images


async def upscale_image(image: Image.Image, workflow_name: str = "LOCAL_UPSCALE"):
    print("queuing workflow:", workflow_name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
        image.save(temp_file, format="PNG")
        temp_filepath = temp_file.name

    # Upload the temporary file using the upload_image method
    response_data = upload_image(temp_filepath)
    filename = response_data["name"]
    with open(config[workflow_name]["CONFIG"], "r") as file:
        workflow = json.load(file)

    generator = ImageGenerator()
    await generator.connect()

    file_input_nodes = config.get(workflow_name, "FILE_INPUT_NODES").split(",")

    for node in file_input_nodes:
        workflow[node]["inputs"]["image"] = filename

    images, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    return images[0]
