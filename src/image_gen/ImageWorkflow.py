from dataclasses import dataclass
from typing import Optional


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
    inpainting_prompt: Optional[str] = None
    inpainting_detection_threshold: Optional[float] = None
    clip_skip: Optional[int] = None
