import configparser

from src.image_gen.ImageWorkflow import *

config = configparser.ConfigParser()
config.read("config.properties")

SD15_GENERATION_DEFAULTS = ImageWorkflow(
    ModelType.SD15, # model_type
    None, # workflow_type
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
    int(config["SD15_GENERATION_DEFAULTS"]["BATCH_SIZE"]),  # batch_size
    None,  # seed
    None,  # filename
    "imagine",  # slash_command
    None,  # inpainting_prompt
    int(config["SD15_GENERATION_DEFAULTS"]["INPAINTING_DETECTION_THRESHOLD"]),  # inpainting_detection_threshold
    int(config["SDXL_GENERATION_DEFAULTS"]["CLIP_SKIP"]),  # clip_skip
)

SDXL_GENERATION_DEFAULTS = ImageWorkflow(
    ModelType.SDXL,  # model_type
    None,  # workflow type
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
    int(config["SDXL_GENERATION_DEFAULTS"]["BATCH_SIZE"]),  # batch_size
    None,  # seed
    None,  # filename
    "sdxl",  # slash_command
    None,  # inpainting_prompt
    int(config["SDXL_GENERATION_DEFAULTS"]["INPAINTING_DETECTION_THRESHOLD"]),  # inpainting_detection_threshold
    int(config["SDXL_GENERATION_DEFAULTS"]["CLIP_SKIP"]),  # clip_skip
    None,   # filename2
    config["SDXL_GENERATION_DEFAULTS"]["ACCELERATOR_ENABLED"],
    config["SDXL_GENERATION_DEFAULTS"]["ACCELERATOR_LORA_NAME"],
    config["SDXL_GENERATION_DEFAULTS"]["SCHEDULER"],
)

CASCADE_GENERATION_DEFAULTS = ImageWorkflow(
    ModelType.CASCADE,  # model_type
    None,  # workflow type
    None,  # prompt
    None,  # negative_prompt
    config["CASCADE_GENERATION_DEFAULTS"]["MODEL"],
    None,  # loras
    None,  # lora_strengths
    config["CASCADE_GENERATION_DEFAULTS"]["ASPECT_RATIO"],  # aspect_ratio
    config["CASCADE_GENERATION_DEFAULTS"]["SAMPLER"],
    int(config["CASCADE_GENERATION_DEFAULTS"]["NUM_STEPS"]),
    float(config["CASCADE_GENERATION_DEFAULTS"]["CFG_SCALE"]),
    float(config["CASCADE_GENERATION_DEFAULTS"]["DENOISE_STRENGTH"]),
    int(config["CASCADE_GENERATION_DEFAULTS"]["BATCH_SIZE"]),  # batch_size
    None,  # seed
    None,  # filename
    "cascade",  # slash_command
    None,  # inpainting_prompt
    int(config["SDXL_GENERATION_DEFAULTS"]["INPAINTING_DETECTION_THRESHOLD"]),  # inpainting_detection_threshold
    int(config["SDXL_GENERATION_DEFAULTS"]["CLIP_SKIP"]),  # clip_skip
)

VIDEO_GENERATION_DEFAULTS = ImageWorkflow(
    ModelType.VIDEO,  # model_type
    None,  # workflow type
    None,  # prompt
    None,  # negative_prompt
    config["VIDEO_GENERATION_DEFAULTS"]["MODEL"],
    None,  # loras
    None,  # lora_strengths
    None,  # aspect_ratio
    config["VIDEO_GENERATION_DEFAULTS"]["SAMPLER"],
    int(config["VIDEO_GENERATION_DEFAULTS"]["NUM_STEPS"]),
    float(config["VIDEO_GENERATION_DEFAULTS"]["CFG_SCALE"]),
    int(config["VIDEO_GENERATION_DEFAULTS"]["BATCH_SIZE"]),  # batch_size
    None,  # denoise_strength
    None,  # seed
    None,  # filename
    "video",  # slash_command
    clip_skip=int(config["SDXL_GENERATION_DEFAULTS"]["CLIP_SKIP"]),  # clip_skip
)

ADD_DETAIL_DEFAULTS = ImageWorkflow(
    None,
    WorkflowType.add_detail,
    None,
    denoise_strength=float(config["ADD_DETAIL_DEFAULTS"]["DENOISE_STRENGTH"]),
    batch_size=int(config["ADD_DETAIL_DEFAULTS"]["BATCH_SIZE"]),
)

UPSCALE_DEFAULTS = ImageWorkflow(
    None,
    WorkflowType.upscale,
    None,
    model=config["UPSCALE_DEFAULTS"]["MODEL"],
)
