from src.image_gen.ImageWorkflow import ImageWorkflow
from src.image_gen.sd_workflows import SDXLWorkflow


async def do_txt2img(params: ImageWorkflow):
    workflow = SDXLWorkflow(params.model, params.clip_skip)
    workflow.create_latents(, params.batch_size)
    workflow.condition_prompts(params.prompt, "")
    workflow.sample(params.seed, params.num_steps, params.cfg_scale, params.sampler, "normal")
    images = workflow.decode_and_save('final_output')
    # convert to Pillow image
    results = images.wait()
    image_batch = [await results.get(i) for i in range(params.batch_size)]
    #image_batch = await ImageBatchResult(results)
    return image_batch