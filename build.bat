@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [NovelTCC] 빌드 시작...

pip install pyinstaller >nul 2>&1

:: 빌드
pyinstaller "%~dp0NovelTCC.spec" --clean --noconfirm --workpath "%~dp0build_tmp" --distpath "%~dp0dist"
if not exist "%~dp0dist\NovelTCC\NovelTCC.exe" (
    echo [실패] 빌드 오류를 확인하세요.
    pause
    exit /b 1
)

:: 빌드 결과물을 현재 경로로 이동
echo [이동 중] 빌드 결과물 이동...
xcopy /e /i /y "%~dp0dist\NovelTCC\_internal" "%~dp0_internal\" >nul
copy /y "%~dp0dist\NovelTCC\NovelTCC.exe" "%~dp0" >nul

:: 임시 폴더 정리
rmdir /s /q "%~dp0build_tmp"
rmdir /s /q "%~dp0dist"

echo.
echo [완료] NovelTCC.exe 가 현재 폴더에 생성되었습니다.
pause
