@ECHO OFF
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

IF NOT EXIST %EMBEDDED_COMFY_LOCATION% (
    git clone https://github.com/comfyanonymous/ComfyUI.git %EMBEDDED_COMFY_LOCATION%
    echo created embedded comfy directory
)

cd %EMBEDDED_COMFY_LOCATION%
pip install -r requirements.txt -U

cd %EMBEDDED_COMFY_LOCATION%\custom_nodes
IF NOT EXIST ComfyScript (
    git clone https://github.com/Chaoses-Ib/ComfyScript.git
    echo cloned ComfyScript
)
cd ComfyScript
python -m pip install -e ".[default]"

cd %EMBEDDED_COMFY_LOCATION%\custom_nodes
IF NOT EXIST was-node-suite-comfyui (
    git clone https://github.com/WASasquatch/was-node-suite-comfyui.git
    echo cloned was node suite
)
cd was-node-suite-comfyui
python -m pip install -r requirements.txt -U

cd %EMBEDDED_COMFY_LOCATION%\custom_nodes
if NOT EXIST ComfyUI_Comfyroll_CustomNodes (
    git clone https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes.git
    ECHO cloned ComfyUI_Comfyroll_CustomNodes
)

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