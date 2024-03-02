import configparser
import contextlib
import os
import random
from typing import Optional
from dataclasses import dataclass
import wave

from comfy_script.runtime import *
from src.util import get_server_address

load(get_server_address())

from comfy_script.runtime.nodes import *

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
    secondary_prompt: Optional[str] = None


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

async def get_data(results):
    output_directory = os.path.join(config["LOCAL"]["COMFY_ROOT_DIR"], "output")
    clip_filenames = []
    video_filenames = []
    video_data = []
    for clip in results._output["clips"]:
        filename = os.path.join(output_directory, clip["filename"])
        clip_filenames.append(filename)
    for video in results._output["videos"]:
        filename = os.path.join(output_directory, video["filename"])
        video_filenames.append(filename)
        with open(filename, "rb") as file:
            video_data.append(file.read())
    return (video_data, video_filenames, clip_filenames)


async def generate_audio(params: AudioWorkflow):
    async with Workflow():
        model, sr = MusicgenLoader()
        raw_audio = MusicgenGenerate(model, params.prompt, 4, params.duration, params.cfg, params.top_k, params.top_p, params.temperature, params.seed or random.randint(0, 2**32 - 1))
        spectrogram_image = SpectrogramImage(raw_audio, 1024, 256, 1024, 0.4)
        spectrogram_image = ImageResize(spectrogram_image, ImageResize.mode.resize, True, ImageResize.resampling.lanczos, 2, 512, 128)
        video = CombineImageWithAudio(spectrogram_image, raw_audio, sr, CombineImageWithAudio.file_format.webm, "final_output")
    results = await video._wait()
    return await get_data(results)


async def extend_audio(params: AudioWorkflow):
    async with Workflow():
        with contextlib.closing(wave.open(params.snd_filename, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            initial_duration = frames / float(rate)
        model, model_sr = MusicgenLoader()
        audio, sr, duration = LoadAudio(params.snd_filename.replace(config["LOCAL"]["COMFY_ROOT_DIR"], "").replace("/output/",""))
        audio = ConvertAudio(audio, sr, model_sr, 1)
        audio = ClipAudio(audio, model_sr, initial_duration - 10.0, duration)
        raw_audio = MusicgenGenerate(model, params.prompt, 4, max(initial_duration + 10, 20), params.cfg, params.top_k, params.top_p, params.temperature, params.seed or random.randint(0, 2**32 - 1), audio)
        raw_audio = ClipAudio(raw_audio, model_sr, 0, initial_duration - 10.0)
        audio = ConcatAudio(audio, raw_audio)
        spectrogram_image = SpectrogramImage(audio, 1024, 256, 1024, 0.4)
        spectrogram_image = ImageResize(spectrogram_image, ImageResize.mode.resize, True, ImageResize.resampling.lanczos, 2, 512, 128)
        video = CombineImageWithAudio(spectrogram_image, audio, model_sr, CombineImageWithAudio.file_format.webm, "final_output")
    results = await video
    return await get_data(results)

async def generate_tts(params: AudioWorkflow):
    async with Workflow():
        model, sr = TortoiseTTSLoader(True, False, False, False)
        raw_audio = TortoiseTTSGenerate(model, params.voice, params.prompt, 4, 8, 8, 0.3, 2, 4, 0.8, 300, 0.7000000000000001, 10, True, 2, 1, params.seed or random.randint(0, 2**32 - 1))
        raw_audio = ConvertAudio(raw_audio, sr, 44100, 1)
        image = SpectrogramImage(raw_audio, 1024, 256, 1024, 0.5, True, True)
        image = ImageResize(image, 'resize', 'true', 'bicubic', 2, 512, 128)
        video = CombineImageWithAudio(image, raw_audio, 44100, 'webm', 'final_output')
    results = await video._wait()
    return await get_data(results)

async def generate_music_with_tts(params: AudioWorkflow):
    async with Workflow():
        model, sr = MusicgenLoader()
        tts_model, tts_sr = TortoiseTTSLoader(True, False, False, False)
        audio = TortoiseTTSGenerate(tts_model, params.voice, params.prompt, 1, 8, 8, 0.3, 2, 4, 0.8, 300, 0.7000000000000001, 10, True, 2, 1, params.seed or random.randint(0, 2**32 - 1))
        audio = ConvertAudio(audio, tts_sr, sr, 1)
        audio = MusicgenGenerate(model, params.secondary_prompt, 4, 15, params.cfg, params.top_k, params.top_p, params.temperature, params.seed or random.randint(0, 2**32 - 1), audio)
        spectrogram_image = SpectrogramImage(audio, 1024, 256, 1024, 0.5, True, True)
        spectrogram_image = ImageResize(spectrogram_image, ImageResize.mode.resize, True, ImageResize.resampling.lanczos, 2, 512, 128)
        SaveImage(spectrogram_image, "spectrogram")
        video = CombineImageWithAudio(spectrogram_image, audio, sr, CombineImageWithAudio.file_format.webm, "final_output")
    results = await video._wait()
    return await get_data(results)