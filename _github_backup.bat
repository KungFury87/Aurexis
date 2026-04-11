@echo off
cd /d "C:\Users\vince\Desktop\Aurexis evolved\back again"

REM Log everything
set "LOG=%~dp0_backup_log.txt"
echo === Aurexis GitHub Backup Log === > "%LOG%"
echo Working dir: %CD% >> "%LOG%" 2>&1
echo. >> "%LOG%"

echo Step 1: Remove old .git >> "%LOG%"
if exist ".git" (
    rmdir /s /q ".git" >> "%LOG%" 2>&1
    echo Removed .git >> "%LOG%"
) else (
    echo No .git found >> "%LOG%"
)

echo Step 2: git init >> "%LOG%"
git init >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED at git init >> "%LOG%"
    echo STATUS=FAILED> "%~dp0_backup_result.txt"
    pause
    exit /b 1
)

echo Step 3: git remote add >> "%LOG%"
git remote add origin https://github.com/KungFury87/Aurexis.git >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED at git remote add >> "%LOG%"
    echo STATUS=FAILED> "%~dp0_backup_result.txt"
    pause
    exit /b 1
)

echo Step 3b: git config user >> "%LOG%"
git config user.email "vincent.anderson.87@gmail.com" >> "%LOG%" 2>&1
git config user.name "Vincent Anderson" >> "%LOG%" 2>&1

echo Step 4: git add -A >> "%LOG%"
git add -A >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED at git add >> "%LOG%"
    echo STATUS=FAILED> "%~dp0_backup_result.txt"
    pause
    exit /b 1
)

echo Step 5: git commit >> "%LOG%"
git commit -m "Aurexis Core V1 Substrate Candidate backup snapshot (11 bridges, 1437 assertions, 21 runners)" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED at git commit >> "%LOG%"
    echo STATUS=FAILED> "%~dp0_backup_result.txt"
    pause
    exit /b 1
)

set "BRANCH=backup/v1-substrate-candidate-20260411"
set "TAG=backup-v1-substrate-candidate-20260411"

echo Step 6: checkout branch %BRANCH% >> "%LOG%"
git checkout -b "%BRANCH%" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED at checkout branch >> "%LOG%"
    echo STATUS=FAILED> "%~dp0_backup_result.txt"
    pause
    exit /b 1
)

echo Step 7: push branch >> "%LOG%"
git push -u origin "%BRANCH%" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED at push branch >> "%LOG%"
    echo STATUS=FAILED> "%~dp0_backup_result.txt"
    pause
    exit /b 1
)

echo Step 8: create tag >> "%LOG%"
git tag -a "%TAG%" -m "Removable backup - Aurexis Core V1 Substrate Candidate, not full Core completion" >> "%LOG%" 2>&1

echo Step 9: push tag >> "%LOG%"
git push origin "%TAG%" >> "%LOG%" 2>&1

echo Step 10: verify >> "%LOG%"
git ls-remote --heads origin "%BRANCH%" >> "%LOG%" 2>&1
git ls-remote --tags origin "%TAG%" >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo BACKUP COMPLETE >> "%LOG%"
echo BRANCH=%BRANCH% >> "%LOG%"
echo TAG=%TAG% >> "%LOG%"

for /f "tokens=*" %%H in ('git rev-parse HEAD') do set "HASH=%%H"
echo HASH=%HASH% >> "%LOG%"

echo BRANCH=%BRANCH%> "%~dp0_backup_result.txt"
echo TAG=%TAG%>> "%~dp0_backup_result.txt"
echo HASH=%HASH%>> "%~dp0_backup_result.txt"
echo STATUS=SUCCESS>> "%~dp0_backup_result.txt"

echo Done! See _backup_log.txt for details.
pause
