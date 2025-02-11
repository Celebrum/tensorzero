@echo off
echo Setting up TensorZero base environment...

:: Check if conda is installed
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Conda not found, installing Miniconda...
    call :install_conda
) else (
    echo Conda found, checking configuration...
    call :check_conda_config
)

:: Create environments directory
if not exist "environments" (
    mkdir environments
    echo Created environments directory
)

:: Create base environment if it doesn't exist
conda env list | findstr /C:"tensorzero_base" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Creating base TensorZero environment...
    call conda env create -f environment.yml -n tensorzero_base
)

echo Setup complete! Run 'conda activate tensorzero_base' to start.
exit /b 0

:install_conda
echo Downloading Miniconda...
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\Miniconda3
del Miniconda3-latest-Windows-x86_64.exe
call %UserProfile%\Miniconda3\Scripts\activate.bat
call conda init
exit /b

:check_conda_config
echo Configuring conda channels...
call conda config --add channels conda-forge --force
call conda config --set channel_priority strict
exit /b