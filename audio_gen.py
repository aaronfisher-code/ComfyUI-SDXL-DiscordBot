import configparser
import json
from dataclasses import dataclass
import os
import tempfile
from typing import Optional

from comfy_api import ComfyGenerator, upload_image


# Read the configuration
config = configparser.ConfigParser()
config.read("config.properties")
server_address = config["LOCAL"]["SERVER_ADDRESS"]


@dataclass
class AudioWorkflow:
    workflow_name: str

    prompt: str
    negative_prompt: Optional[str] = None

    voice: Optional[str] = None

    duration: Optional[float] = None
    cfg: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[int] = None
    temperature: Optional[float] = None

    seed: Optional[int] = None

    snd_filename: Optional[list[str]] = None
    vid_filename: Optional[list[str]] = None


MUSICGEN_DEFAULTS = AudioWorkflow(
    None,
    None,
    duration=float(config["MUSICGEN_DEFAULTS"]["DURATION"]),
    cfg=float(config["MUSICGEN_DEFAULTS"]["CFG"]),
    top_k=int(config["MUSICGEN_DEFAULTS"]["TOP_K"]),
    top_p=float(config["MUSICGEN_DEFAULTS"]["TOP_P"]),
    temperature=float(config["MUSICGEN_DEFAULTS"]["TEMPERATURE"]),
)


TORTOISE_DEFAULTS = AudioWorkflow(
    None,
    None,
    voice=config["TORTOISE_DEFAULTS"]["VOICE"],
    top_p=float(config["TORTOISE_DEFAULTS"]["TOP_P"]),
    temperature=float(config["TORTOISE_DEFAULTS"]["TEMPERATURE"]),
)


def setup_workflow(workflow, params: AudioWorkflow):
    prompt_nodes = config.get(params.workflow_name, "PROMPT_NODES").split(",")
    rand_seed_nodes = config.get(params.workflow_name, "RAND_SEED_NODES").split(",")
    generator_nodes = config.get(params.workflow_name, "GENERATOR_NODE").split(",")

    voice_nodes = None
    if config.has_option(params.workflow_name, "VOICE_NODES"):
        voice_nodes = config.get(params.workflow_name, "VOICE_NODES").split(",")

    file_input_nodes = None
    if config.has_option(params.workflow_name, "FILE_INPUT_NODES"):
        file_input_nodes = config.get(params.workflow_name, "FILE_INPUT_NODES").split(",")

    # Modify the prompt dictionary
    if params.prompt is not None and prompt_nodes[0] != "":
        for node in prompt_nodes:
            if "text" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["text"] = params.prompt
            elif "prompt" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["prompt"] = params.prompt

    if params.snd_filename is not None and file_input_nodes is not None:
        for node in file_input_nodes:
            workflow[node]["inputs"]["path"] = params.snd_filename

    if rand_seed_nodes[0] != "":
        for node in rand_seed_nodes:
            workflow[node]["inputs"]["seed"] = params.seed

    if params.voice is not None and voice_nodes is not None:
        for node in voice_nodes:
            workflow[node]["inputs"]["voice"] = params.voice

    for node in generator_nodes:
        inputs = workflow[node]["inputs"]
        if "duration" in inputs and params.duration is not None:
            inputs["duration"] = params.duration
        if "cfg" in inputs and params.cfg is not None:
            inputs["cfg"] = params.cfg
        if "top_k" in inputs and params.top_k is not None:
            inputs["top_k"] = params.top_k
        if "top_p" in inputs and params.top_p is not None:
            inputs["top_p"] = params.top_p
        if "temperature" in inputs and params.temperature is not None:
            inputs["temperature"] = params.temperature
        workflow[node]["inputs"] = inputs

    return workflow


async def generate_audio(params: AudioWorkflow):
    print("queuing workflow:", params)
    with open(config[params.workflow_name]["CONFIG"], "r") as file:
        workflow = json.load(file)

    generator = ComfyGenerator()
    await generator.connect()

    setup_workflow(workflow, params)

    images, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    clips = images["clips"]
    clips, clip_fnames = zip(*clips)
    videos = images["videos"]
    videos, video_fnames = zip(*videos)

    # params.snd_filename = clip_fnames
    # params.vid_filename = video_fnames

    return (clips, videos, clip_fnames), enhanced_prompt


# async def generate_alternatives(params: ImageWorkflow, image: Image.Image):
#     print("queuing workflow:", params)
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
#         image.save(temp_file, format="PNG")
#         temp_filepath = temp_file.name

#     # Upload the temporary file using the upload_image method
#     response_data = upload_image(temp_filepath)
#     filename = response_data["name"]
#     params.filename = filename

#     with open(config[params.workflow_name]["CONFIG"], "r") as file:
#         workflow = json.load(file)

#     generator = ImageGenerator()
#     await generator.connect()

#     setup_workflow(workflow, params)

#     images, enhanced_prompt = await generator.get_images(workflow)
#     await generator.close()

#     return images


# async def upscale_image(image: Image.Image, workflow_name: str = "LOCAL_UPSCALE"):
#     print("queuing workflow:", workflow_name)
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
#         image.save(temp_file, format="PNG")
#         temp_filepath = temp_file.name

#     # Upload the temporary file using the upload_image method
#     response_data = upload_image(temp_filepath)
#     filename = response_data["name"]
#     with open(config[workflow_name]["CONFIG"], "r") as file:
#         workflow = json.load(file)

#     generator = ImageGenerator()
#     await generator.connect()

#     file_input_nodes = config.get(workflow_name, "FILE_INPUT_NODES").split(",")

#     for node in file_input_nodes:
#         workflow[node]["inputs"]["image"] = filename

#     images, enhanced_prompt = await generator.get_images(workflow)
#     await generator.close()

#     return images[0]
