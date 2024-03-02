@ECHO OFF
:: TORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu118  :: for cuda 11.8
:: CUDA_VER=11.8
set TORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu121
set CUDA_VER=12.1

IF NOT EXIST venv (
    python -m venv --copies venv
    echo created new virtualenv
)

call venv\Scripts\activate
pip install -r requirements.txt

IF NOT EXIST config.properties (
    copy config.properties.example config.properties
    echo copied example config to config.properties
    echo add your bot token and comfyui server address to this config
) ELSE (
    echo found existing config.properties; not overwriting
)

set ROOT_DIR=%cd%
set EMBEDDED_COMFY_LOCATION="%ROOT_DIR%\embedded_comfy"

mkdir input
mkdir out

IF NOT EXIST %EMBEDDED_COMFY_LOCATION% (
    git clone https://github.com/comfyanonymous/ComfyUI.git %EMBEDDED_COMFY_LOCATION%
    echo created embedded comfy directory
)

cd %EMBEDDED_COMFY_LOCATION%
pip install -r requirements.txt -U --extra-index-url %TORCH_CUDA_INDEX_URL%

cd %EMBEDDED_COMFY_LOCATION%\custom_nodes
IF NOT EXIST ComfyScript (
    git clone https://github.com/Chaoses-Ib/ComfyScript.git
    echo cloned ComfyScript
)
cd ComfyScript
python -m pip install -e ".[default]"

IF NOT EXIST %EMBEDDED_COMFY_LOCATION%/ComfyUI_Ib_CustomNodes (
    git clone https://github.com/Chaoses-Ib/ComfyUI_Ib_CustomNodes.git
    echo cloned ComfyUI_Ib_CustomNodes
)
cd %EMBEDDED_COMFY_LOCATION%/ComfyUI_Ib_CustomNodes
python -m pip install -r requirements.txt -U --extra-index-url %TORCH_CUDA_INDEX_URL%

cd %EMBEDDED_COMFY_LOCATION%\custom_nodes
IF NOT EXIST was-node-suite-comfyui (
    git clone https://github.com/WASasquatch/was-node-suite-comfyui.git
    echo cloned was node suite
)
cd was-node-suite-comfyui
python -m pip install -r requirements.txt -U --extra-index-url %TORCH_CUDA_INDEX_URL%

cd %EMBEDDED_COMFY_LOCATION%\custom_nodes
if NOT EXIST ComfyUI_Comfyroll_CustomNodes (
    git clone https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git
    ECHO cloned ComfyUI_Comfyroll_CustomNodes
)

IF NOT EXIST %EMBEDDED_COMFY_LOCATION%/ComfyUI-AnimateDiff-Evolved (
    git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
    echo cloned ComfyUI-AnimateDiff-Evolved
)

IF NOT EXIST %EMBEDDED_COMFY_LOCATION%/ComfyUI-VideoHelperSuite (
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    echo cloned ComfyUI-VideoHelperSuite
)
cd %EMBEDDED_COMFY_LOCATION%/ComfyUI-VideoHelperSuite
python -m pip install -r requirements.txt -U --extra-index-url %TORCH_CUDA_INDEX_URL%

cd %EMBEDDED_COMFY_LOCATION%/models/checkpoints
mkdir xl
mkdir 15
mkdir cascade

cd %EMBEDDED_COMFY_LOCATION%/models/loras
mkdir xl
mkdir 15
mkdir cascade

cd %EMBEDDED_COMFY_LOCATION%/models/controlnet
mkdir xl
mkdir 15
mkdir cascade

cd %EMBEDDED_COMFY_LOCATION%
python main.py --quick-test-for-ci