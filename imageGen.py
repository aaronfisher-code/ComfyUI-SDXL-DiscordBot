import configparser
import json
import tempfile
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from comfy_api import ComfyGenerator as ImageGenerator, upload_image


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
    batch_size: Optional[int] = None

    seed: Optional[int] = None
    filename: str = None
    slash_command: str = None


# Read the configuration
config = configparser.ConfigParser()
config.read("config.properties")
server_address = config["LOCAL"]["SERVER_ADDRESS"]

SD15_GENERATION_DEFAULTS = ImageWorkflow(
    None,  # workflow name
    None,  # prompt
    None,  # negative_prompt
    config["SD15_GENERATION_DEFAULTS"]["MODEL"],
    None,  # loras
    None,  # lora_strengths TODO add lora and lora strength defaults
    config["SD15_GENERATION_DEFAULTS"]["ASPECT_RATIO"],
    config["SD15_GENERATION_DEFAULTS"]["SAMPLER"],
    int(config["SD15_GENERATION_DEFAULTS"]["NUM_STEPS"]),
    float(config["SD15_GENERATION_DEFAULTS"]["CFG_SCALE"]),
    float(config["SD15_GENERATION_DEFAULTS"]["DENOISE_STRENGTH"]),
    None,  # seed
    None,  # filename
    "imagine"  # slash_command
)

SDXL_GENERATION_DEFAULTS = ImageWorkflow(
    None,  # workflow name
    None,  # prompt
    None,  # negative_prompt
    config["SDXL_GENERATION_DEFAULTS"]["MODEL"],
    None,  # loras
    None,  # lora_strengths
    config["SDXL_GENERATION_DEFAULTS"]["ASPECT_RATIO"],
    config["SDXL_GENERATION_DEFAULTS"]["SAMPLER"],
    int(config["SDXL_GENERATION_DEFAULTS"]["NUM_STEPS"]),
    float(config["SDXL_GENERATION_DEFAULTS"]["CFG_SCALE"]),
    float(config["SDXL_GENERATION_DEFAULTS"]["DENOISE_STRENGTH"]),
    None,  # seed
    None,  # filename
    "sdxl"  # slash_command
)

VIDEO_GENERATION_DEFAULTS = ImageWorkflow(
    None,  # workflow name
    None,  # prompt
    None,  # negative_prompt
    config["VIDEO_GENERATION_DEFAULTS"]["MODEL"],
    None,  # loras
    None,  # lora_strengths
    None,  # aspect_ratio
    config["VIDEO_GENERATION_DEFAULTS"]["SAMPLER"],
    int(config["VIDEO_GENERATION_DEFAULTS"]["NUM_STEPS"]),
    float(config["VIDEO_GENERATION_DEFAULTS"]["CFG_SCALE"]),
    None,  # denoise_strength
    None,  # seed
    None,  # filename
    "video"  # slash_command
)


def setup_workflow(workflow, params: ImageWorkflow):
    prompt_nodes = config.get(params.workflow_name, "PROMPT_NODES").split(",")
    neg_prompt_nodes = config.get(params.workflow_name, "NEG_PROMPT_NODES").split(",")
    rand_seed_nodes = config.get(params.workflow_name, "RAND_SEED_NODES").split(",")
    model_node = config.get(params.workflow_name, "MODEL_NODE").split(",")
    lora_node = config.get(params.workflow_name, "LORA_NODE").split(",")
    llm_model_node = None
    turbo_lora_node = None

    if config.has_option(params.workflow_name, "FILE_INPUT_NODES"):
        file_input_nodes = config.get(params.workflow_name, "FILE_INPUT_NODES").split(",")

    if config.has_option(params.workflow_name, "LLM_MODEL_NODE"):
        llm_model_node = config.get(params.workflow_name, "LLM_MODEL_NODE")

    if config.has_option(params.workflow_name, "TURBO_LORA_NODE"):
        turbo_lora_node = config.get(params.workflow_name, "TURBO_LORA_NODE")

    # Modify the prompt dictionary
    if params.prompt is not None and prompt_nodes[0] != "":
        for node in prompt_nodes:
            if "text" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["text"] = params.prompt
            elif "prompt" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["prompt"] = params.prompt

    if neg_prompt_nodes[0] != "":
        neg_prompt = (params.negative_prompt or "") + ", (children, child, kids, kid, teens, teen:1.3)"
        for node in neg_prompt_nodes:
            if "text" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["text"] = neg_prompt
            elif "prompt" in workflow[node]["inputs"]:
                workflow[node]["inputs"]["prompt"] = neg_prompt

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

    if params.aspect_ratio is not None and config.has_option(params.workflow_name, "EMPTY_IMAGE_NODE"):
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
    if params.batch_size is not None and config.has_option(params.workflow_name, "LATENT_IMAGE_NODE"):
        latent_image_node = config.get(params.workflow_name, "LATENT_IMAGE_NODE").split(",")
        for node in latent_image_node:
            workflow[node]["inputs"]["amount"] = params.batch_size

    if turbo_lora_node is not None and config.get("SDXL_GENERATION_DEFAULTS", "TURBO_ENABLED") == "False":
        if "lora_01" in workflow[turbo_lora_node]["inputs"]:
            workflow[turbo_lora_node]["inputs"]["lora_01"] = "None"
        elif "switch_1" in workflow[turbo_lora_node]["inputs"]:
            workflow[turbo_lora_node]["inputs"]["switch_1"] = "Off"

    return workflow


async def generate_images(params: ImageWorkflow):
    print("queuing workflow:", params)
    with open(config[params.workflow_name]["CONFIG"], "r") as file:
        workflow = json.load(file)

    generator = ImageGenerator()
    await generator.connect()

    setup_workflow(workflow, params)

    output, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    images = [*output["images"], *output["gifs"]]
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

    output, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    images = [*output["images"], *output["gifs"]]
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

    output, enhanced_prompt = await generator.get_images(workflow)
    await generator.close()

    images = [*output["images"], *output["gifs"]]
    return images[0]
