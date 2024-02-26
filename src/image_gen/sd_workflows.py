import dataclasses
from typing import Optional

import PIL.Image
from comfy.cli_args_types import Configuration
from comfy.client.embedded_comfy_client import EmbeddedComfyClient

from comfy_script.runtime import *

load("http://127.0.0.1:8123")

from comfy_script.runtime.nodes import *
from src.image_gen.ImageWorkflow import ImageWorkflow

sd_aspect_ratios = {
    "1:1": (1024, 1024),
    "3:4 portrait": (896, 1152),
    "9:16 portrait": (768, 1344),
    "4:3 landscape": (1152, 896),
    "16:9 landscape": (1344, 768),
}


@dataclasses.dataclass
class Lora:
    name: str
    strength: float


class SDWorkflow:
    def __init__(self, model_name: str, clip_skip: int, loras: Optional[list[Lora]] = None):
        self._load_model(model_name, clip_skip, loras)

    def _load_model(self, model_name: str, clip_skip: int, loras: Optional[list[Lora]] = None):
        model, clip, vae = CheckpointLoaderSimple(model_name)
        if loras:
            for lora in loras:
                model, clip = LoraLoader(model, clip, lora.name, lora.strength, lora.strength)
        clip = CLIPSetLastLayer(clip, clip_skip)
        self.model = model
        self.clip = clip
        self.vae = vae

    def create_latents(self, dimensions: tuple[int, int], batches: int):
        width, height = dimensions
        latent = EmptyLatentImage(width, height, batches)
        self.latents = [latent]

    def create_img2img_latents(self, image_input: Image, batches: int):
        latent = VAEEncode(image_input, self.vae)
        if batches > 1:
            latent = RepeatLatentBatch(latent, batches)
        self.latents = [latent]

    def condition_prompts(self, positive_prompt: str, negative_prompt: str):
        self.conditioning = CLIPTextEncode(positive_prompt, self.clip)
        self.negative_conditioning = CLIPTextEncode(negative_prompt, self.clip)

    def mask_for_inpainting(self, image_input: Image, inpainting_prompt: str, threshold: float):
        clip_seg_model = CLIPSegModelLoader("CIDAS/clipseg-rd64-refined")
        masking, _ = CLIPSegMasking(image_input, inpainting_prompt, clip_seg_model)
        masking = MaskDominantRegion(masking, threshold)
        self.latents[0] = SetLatentNoiseMask(self.latents[0], masking)

    def sample(self, seed: int, num_samples: int, cfg_scale: float, sampler_name: str, scheduler: str, denoise_strength: float = 1):
        self.output_latents = KSampler(self.model, seed, num_samples, cfg_scale, sampler_name, scheduler, self.conditioning, self.negative_conditioning, self.latents[0], denoise_strength)

    def decode(self):
        return VAEDecode(self.output_latents, self.vae)

    def decode_and_save(self, file_name: str):
        image = VAEDecode(self.output_latents, self.vae)
        return SaveImage(image, file_name)


class SD15Workflow(SDWorkflow):
    pass


class SDXLWorkflow(SDWorkflow):
    def condition_prompts(self, positive_prompt: str, negative_prompt: str):
        self.conditioning = CLIPTextEncodeSDXL(4096, 4096, 4096, 4096, 4096, 4096, positive_prompt, self.clip, positive_prompt)
        self.negative_conditioning = CLIPTextEncode(negative_prompt, self.clip)


class SDCascadeWorkflow(SDWorkflow):
    def _load_model(self, model_name: str, clip_skip: int, loras: Optional[list[Lora]] = None):
        self.model, self.clip, self.stage_c_vae, self.clip_vision = UnCLIPCheckpointLoader(model_name)
        self.stage_b_model, self.stage_b_clip, self.vae = CheckpointLoaderSimple(Checkpoints.cascade_stable_cascade_stage_b)

    def create_latents(self, dimensions: tuple[int, int], batches: int):
        width, height = dimensions
        latent_c, latent_b = StableCascadeEmptyLatentImage(width, height, 42, batches)
        self.latents = [latent_c, latent_b]

    def create_img2img_latents(self, image_input: Image, batches: int):
        stage_c, stage_b = StableCascadeStageCVAEEncode(image_input, self.stage_c_vae, 32)
        stage_c = RepeatLatentBatch(stage_c, batches)
        stage_b = RepeatLatentBatch(stage_b, batches)
        self.latents = [stage_c, stage_b]

    def unclip_encode(self, image_input: list[Image]):
        for input in image_input:
            encoded_clip_vision = CLIPVisionEncode(self.clip_vision, input)
            self.conditioning = UnCLIPConditioning(self.conditioning, encoded_clip_vision)

    def condition_prompts(self, positive_prompt: str, negative_prompt: str):
        self.conditioning = CLIPTextEncode(positive_prompt, self.clip)
        self.stage_c_conditioning = self.conditioning
        self.negative_conditioning = CLIPTextEncode(negative_prompt, self.clip)

    def sample(self, seed: int, num_samples: int, cfg_scale: float, sampler_name: str, scheduler: str, denoise_strength: float = 1):
        stage_c = KSampler(self.model, seed, num_samples, cfg_scale, sampler_name, scheduler, self.conditioning, self.negative_conditioning, self.latents[0], denoise_strength)
        self.stage_b_conditioning = StableCascadeStageBConditioning(self.stage_c_conditioning, self.latents[0])
        conditioning2 = StableCascadeStageBConditioning(self.stage_c_conditioning, stage_c)
        zeroed_out = ConditioningZeroOut(self.stage_c_conditioning)
        self.output_latents = KSampler(self.stage_b_model, seed, 10, 1.1, sampler_name, scheduler, conditioning2, zeroed_out, self.latents[1], 1)


class UpscaleWorkflow:
    def load_image(self, file_path: str):
        self.image, _ = LoadImage(file_path)

    def pass_image(self, image):
        self.image = image

    def upscale(self, rescale_factor: float):
        self.image, _ = CRUpscaleImage(self.image, UpscaleModels.RealESRGAN_x4plus, 'rescale', rescale_factor, 1024, CRUpscaleImage.resampling_method.lanczos, True, 8)

    def save(self, file_path: str):
        return SaveImage(self.image, file_path)


def do_txt2img(
        workflow: SDWorkflow,
        prompt: str,
        negative_prompt: str,
        steps: int,
        cfg_scale: float,
        seed: int,
        model: str,
        dimensions: tuple[int, int],
        batches: int,
        sampler_name: str,
        scheduler: str,
        clip_skip: int,
        loras: Optional[list[Lora]]
):
    workflow.load_model(model, clip_skip, loras)
    workflow.create_latents(*dimensions, batches)
    workflow.condition_prompts(prompt, negative_prompt)
    workflow.sample(seed, steps, cfg_scale, sampler_name, scheduler)
    return workflow


def do_img2img(
        workflow: SDWorkflow,
        image_input: Image,
        prompt: str,
        negative_prompt: str,
        steps: int,
        cfg_scale: float,
        seed: int,
        model: str,
        batches: int,
        sampler_name: str,
        scheduler: str,
        denoise_strength: float,
        clip_skip: int,
        loras: Optional[list[Lora]] = None
):
    workflow.load_model(model, clip_skip, loras)
    workflow.create_img2img_latents(image_input, batches)
    workflow.condition_prompts(prompt, negative_prompt)
    workflow.sample(seed, steps, cfg_scale, sampler_name, scheduler, denoise_strength)
    return workflow

async def do_txt2img_a(params: ImageWorkflow):
    workflow = SDXLWorkflow(Checkpoints.xl_juggernautXL_version6Rundiffusion, params.clip_skip)
    workflow.create_latents((1024, 1024), params.batch_size)
    workflow.condition_prompts(params.prompt, "")
    workflow.sample(params.seed, params.num_steps, params.cfg_scale, params.sampler, "normal")
    images = workflow.decode_and_save('final_output')
    results = images.wait()
    image_batch = [await results.get(i) for i in range(params.batch_size)]
    return image_batch
