@REM @ECHO OFF
IF NOT EXIST venv (
    python -m venv --copies venv
    echo created new virtualenv
)

@REM conda activate comfybot-embedded
@REM call venv\Scripts\activate
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
    mkdir %EMBEDDED_COMFY_LOCATION%
    echo created embedded comfy directory
)

comfyui --cwd=%EMBEDDED_COMFY_LOCATION% --create_directories --quick-test-for-ci

cd %EMBEDDED_COMFY_LOCATION%\custom_nodes
IF NOT EXIST ComfyScript (
    git clone https://github.com/Chaoses-Ib/ComfyScript.git
    echo cloned ComfyScript
)
cd ComfyScript
python -m pip install -e ".[default]"

cd %EMBEDDED_COMFY_LOCATION%\checkpoints
mkdir xl
mkdir 15
mkdir cascade

cd %EMBEDDED_COMFY_LOCATION%\loras
mkdir xl
mkdir 15
mkdir cascade

cd %EMBEDDED_COMFY_LOCATION%\controlnet
mkdir xl
mkdir 15
mkdir cascade