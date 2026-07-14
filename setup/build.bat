@echo off
setlocal
REM ============================================================
REM  AFSIS Search Pictures - build do executavel Windows
REM  Pode ser executado de qualquer pasta (ajusta o diretorio sozinho)
REM  Resultado: dist\AFSISSearchPictures.exe (onefile)
REM ============================================================

REM Muda para a raiz do projeto (pasta acima deste script)
cd /d "%~dp0.."
echo Raiz do projeto: %CD%
echo.

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
if errorlevel 1 goto :erro
python -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib pillow
if errorlevel 1 goto :erro

python -m PyInstaller --clean --noconfirm setup\AFSISSearchPictures.spec
if errorlevel 1 goto :erro

echo.
echo Executavel gerado em %CD%\dist\AFSISSearchPictures.exe
goto :fim

:erro
echo.
echo Falha no build. Verifique as mensagens acima.

:fim
pause
