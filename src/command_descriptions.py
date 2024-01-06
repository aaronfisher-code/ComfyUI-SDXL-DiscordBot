import json

from discord.app_commands import Choice

from comfy_api import models, loras, samplers
from consts import *
from image_gen.defaults import *

generation_messages = json.loads(open("generation_messages.json", "r").read())
completion_messages = json.loads(open("completion_messages.json", "r").read())

# These aspect ratio resolution values correspond to the SDXL Empty Latent Image node.
# A latent modification node in the workflow converts it to the equivalent SD 1.5 resolution values.
ASPECT_RATIO_CHOICES = [
    Choice(name="1:1", value="1024 x 1024  (square)"),
    Choice(name="7:9 portrait", value=" 896 x 1152  (portrait)"),
    Choice(name="4:7 portrait", value=" 768 x 1344  (portrait)"),
    Choice(name="9:7 landscape", value="1152 x 896   (landscape)"),
    Choice(name="7:4 landscape", value="1344 x 768   (landscape)"),
]
SD15_MODEL_CHOICES = [Choice(name=m.replace(".safetensors", ""), value=m) for m in models[0] if "xl" not in m.lower()][:25]
SD15_LORA_CHOICES = [Choice(name=l.replace(".safetensors", ""), value=l) for l in loras[0] if "xl" not in l.lower()][:25]
SDXL_MODEL_CHOICES = [Choice(name=m.replace(".safetensors", ""), value=m) for m in models[0] if "xl" in m.lower() and "refiner" not in m.lower()][:25]
SDXL_LORA_CHOICES = [Choice(name=l.replace(".safetensors", ""), value=l) for l in loras[0] if "xl" in l.lower()][:25]
SAMPLER_CHOICES = [Choice(name=s, value=s) for s in samplers[0]]

BASE_ARG_DESCS = {
    "prompt": "Prompt for the image being generated",
    "negative_prompt": "Prompt for what you want to steer the AI away from",
    "model": "Model checkpoint to use",
    "lora": "LoRA to apply",
    "lora_strength": "Strength of LoRA",
    "aspect_ratio": "Aspect ratio of the generated image",
    "sampler": "Sampling algorithm to use",
    "num_steps": f"range [1, {MAX_STEPS}]; Number of sampling steps",
    "cfg_scale": f"range [1.0, {MAX_CFG}]; Degree to which AI should follow prompt",
}
IMAGINE_ARG_DESCS = {
    **BASE_ARG_DESCS,
    "num_steps": "Number of sampling steps; range [1, 30]",
    "input_file": "Image to use as input for img2img",
    "denoise_strength": f"range [0.01, 1.0], default {SD15_GENERATION_DEFAULTS.denoise_strength}; Strength of denoising filter during img2img. Only works when input_file is set",
    "inpainting_prompt": "Detection prompt for inpainting; examples: 'background' or 'person'",
    "inpainting_detection_threshold": f"range [0, 255], default {SD15_GENERATION_DEFAULTS.inpainting_detection_threshold}; Detection threshold for inpainting. Only works when inpainting_prompt is set"
}
SDXL_ARG_DESCS = {
    **BASE_ARG_DESCS,
    "input_file": "Image to use as input for img2img",
    "denoise_strength": f"range [0.01, 1.0], default {SDXL_GENERATION_DEFAULTS.denoise_strength}; Strength of denoising filter during img2img. Only works when input_file is set",
    "inpainting_prompt": "Detection prompt for inpainting; examples: 'background' or 'person'",
    "inpainting_detection_threshold": f"range [0, 255], default {SDXL_GENERATION_DEFAULTS.inpainting_detection_threshold}; Detection threshold for inpainting. Only works when inpainting_prompt is set"
}
VIDEO_ARG_DESCS = {k: v for k, v in BASE_ARG_DESCS.items() if k != "aspect_ratio"}

BASE_ARG_CHOICES = {
    "aspect_ratio": ASPECT_RATIO_CHOICES,
    "sampler": SAMPLER_CHOICES,
}
IMAGINE_ARG_CHOICES = {
    "model": SD15_MODEL_CHOICES,
    "lora": SD15_LORA_CHOICES,
    "lora2": SD15_LORA_CHOICES,
    **BASE_ARG_CHOICES,
}
SDXL_ARG_CHOICES = {
    "model": SDXL_MODEL_CHOICES,
    "lora": SDXL_LORA_CHOICES,
    "lora2": SDXL_LORA_CHOICES,
    **BASE_ARG_CHOICES,
}
VIDEO_ARG_CHOICES = {
    k: v for k, v in IMAGINE_ARG_CHOICES.items() if k not in {"lora2", "lora3", "aspect_ratio"}
}
