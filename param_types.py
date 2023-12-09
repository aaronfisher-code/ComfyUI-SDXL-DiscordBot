from dataclasses import dataclass
from discord.app_commands import Choice, Range

@dataclass
class PromptParams:
    prompt: str = None
    negative_prompt: str = None


@dataclass
class ModelParams:
    model: str = None
    lora: Choice[str] = None
    lora_strength: float = 1.0
    lora2: Choice[str] = None
    lora_strength2: float = 1.0
    lora3: Choice[str] = None
    lora_strength3: float = 1.0


@dataclass
class ImageParams:
    aspect_ratio: str = None


@dataclass
class SamplerParams:
    num_steps: Range[int, 1, 20] = None
    cfg_scale: Range[float, 1.0, 10.0] = None
    seed: int = None
    batch_size: int = 4


@dataclass
class WorkflowParams:
    config: str = None