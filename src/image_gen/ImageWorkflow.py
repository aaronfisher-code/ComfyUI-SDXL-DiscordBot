from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ModelType(Enum):
    SD15 = "SD15",
    SDXL = "SDXL",
    CASCADE = "CASCADE",
    VIDEO = "VIDEO",

class WorkflowType(Enum):
    txt2img = "txt2img",
    img2img = "img2img",
    upscale = "upscale",
    add_detail = "add_detail",
    image_mashup = "image_mashup",
    video = "video",

sd_aspect_ratios = {
    "1:1": (1024, 1024),
    "3:4 portrait": (896, 1152),
    "9:16 portrait": (768, 1344),
    "4:3 landscape": (1152, 896),
    "16:9 landscape": (1344, 768),
}

@dataclass
class ImageWorkflow:
    model_type: ModelType
    workflow_type: WorkflowType

    prompt: str
    negative_prompt: Optional[str] = None

    model: Optional[str] = None
    loras: Optional[list[str]] = None
    lora_strengths: Optional[list[float]] = None

    dimensions: Optional[tuple[int, int]] = None
    sampler: Optional[str] = None
    num_steps: Optional[int] = None
    cfg_scale: Optional[float] = None

    denoise_strength: Optional[float] = None
    batch_size: Optional[int] = None

    seed: Optional[int] = None
    filename: str = None
    slash_command: str = None
    inpainting_prompt: Optional[str] = None
    inpainting_detection_threshold: Optional[float] = None
    clip_skip: Optional[int] = None
    filename2: Optional[str] = None
    use_accelerator_lora: Optional[bool] = None
    accelerator_lora_name: Optional[str] = None
    scheduler: Optional[str] = None
