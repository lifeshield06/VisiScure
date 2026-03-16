@echo off
echo Installing gTTS (Google Text-to-Speech) for voice announcements...
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install gTTS
echo Installing gTTS...
pip install gTTS==2.5.0

echo.
echo Installation complete!
echo.
echo gTTS has been installed successfully.
echo The waiter call system will now generate voice announcements.
echo.
pause
