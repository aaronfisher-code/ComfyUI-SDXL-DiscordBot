from src.image_gen.ImageWorkflow import *
from src.image_gen.sd_workflows import *

model_type_to_workflow = {
    ModelType.SD15: SD15Workflow,
    ModelType.SDXL: SDXLWorkflow,
    ModelType.CASCADE: SDCascadeWorkflow
}

async def _do_txt2img(params: ImageWorkflow, model_type: ModelType):
    workflow = model_type_to_workflow[model_type](params.model, params.clip_skip)
    workflow.create_latents(params.dimensions, params.batch_size)
    workflow.condition_prompts(params.prompt, params.negative_prompt)
    workflow.sample(params.seed, params.num_steps, params.cfg_scale, params.sampler, "normal")
    images = workflow.decode_and_save('final_output')
    results = images.wait()
    image_batch = [await results.get(i) for i in range(params.batch_size)]
    return image_batch



async def do_workflow(params: ImageWorkflow):
    match params.workflow_type:
        case WorkflowType.txt2img:
            return await _do_txt2img(params, params.model_type)
        # case WorkflowType.img2img:
        #     return await _do_img2img(params, params.model_type)
        # case WorkflowType.upscale:
        #     return await _do_upscale(params, params.model_type)
        # case WorkflowType.add_detail:
        #     return await _do_add_detail(params, params.model_type)
        case _:
            raise ValueError(f"Invalid workflow type: {params.workflow_type}")