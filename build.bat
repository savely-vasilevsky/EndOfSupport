@echo off
echo Building AWS End-of-Support Tool...
echo.

REM Clean previous builds
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Build the executable
pyinstaller EndOfSupportTool.spec --clean

echo.
if exist "dist\EndOfSupportTool.exe" (
    echo Build successful!
    echo Executable: dist\EndOfSupportTool.exe
) else (
    echo Build failed!
)
pause
