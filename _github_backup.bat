@echo off
setlocal enabledelayedexpansion

REM ── Aurexis Core GitHub Backup Script ──
REM Pushes current repo state to a removable backup branch + tag
REM Recovered Page Sequence Signature Bridge V1 (13th bridge)

set "REPO_DIR=%~dp0"
set "BRANCH=backup/v1-substrate-candidate-20260411-seqsig"
set "TAG=backup-v1-substrate-candidate-20260411-seqsig"
set "LOG=%REPO_DIR%_backup_log.txt"
set "GCM_GITHUBAUTHMODE=device"

echo ============================================ > "%LOG%"
echo Aurexis Core GitHub Backup >> "%LOG%"
echo Recovered Page Sequence Signature Bridge V1 >> "%LOG%"
echo %date% %time% >> "%LOG%"
echo ============================================ >> "%LOG%"

cd /d "%REPO_DIR%"

REM Check if .git exists
if exist ".git" (
    echo Git repo found, updating... >> "%LOG%"

    REM Add all files
    echo Adding files... >> "%LOG%"
    git add -A >> "%LOG%" 2>&1

    REM Configure identity
    git config user.email "vincent.anderson.87@gmail.com" >> "%LOG%" 2>&1
    git config user.name "Vincent Anderson" >> "%LOG%" 2>&1

    REM Commit
    echo Committing... >> "%LOG%"
    git commit -m "Recovered Page Sequence Signature Bridge V1 — 13th bridge milestone, 1740 assertions, 23 runners, 25 modules" >> "%LOG%" 2>&1

    REM Create backup branch
    echo Creating branch %BRANCH%... >> "%LOG%"
    git checkout -B "%BRANCH%" >> "%LOG%" 2>&1

    REM Create tag
    echo Creating tag %TAG%... >> "%LOG%"
    git tag -f "%TAG%" -m "Backup: V1 Substrate Candidate with Page Sequence Signature Bridge (13th bridge)" >> "%LOG%" 2>&1

    REM Push branch
    echo Pushing branch... >> "%LOG%"
    git push -u origin "%BRANCH%" --force >> "%LOG%" 2>&1
    echo Push branch exit code: !errorlevel! >> "%LOG%"

    REM Push tag
    echo Pushing tag... >> "%LOG%"
    git push origin "%TAG%" --force >> "%LOG%" 2>&1
    echo Push tag exit code: !errorlevel! >> "%LOG%"

    REM Verify
    echo Verifying remote... >> "%LOG%"
    git ls-remote origin "%BRANCH%" >> "%LOG%" 2>&1
    git ls-remote origin "refs/tags/%TAG%" >> "%LOG%" 2>&1

    echo ============================================ >> "%LOG%"
    echo DONE >> "%LOG%"
    echo %date% %time% >> "%LOG%"

) else (
    echo No .git found, initializing... >> "%LOG%"
    git init >> "%LOG%" 2>&1
    git config user.email "vincent.anderson.87@gmail.com" >> "%LOG%" 2>&1
    git config user.name "Vincent Anderson" >> "%LOG%" 2>&1
    git remote add origin https://github.com/KungFury87/Aurexis.git >> "%LOG%" 2>&1
    git add -A >> "%LOG%" 2>&1
    git commit -m "Recovered Page Sequence Signature Bridge V1 — 13th bridge milestone, 1740 assertions, 23 runners, 25 modules" >> "%LOG%" 2>&1
    git checkout -B "%BRANCH%" >> "%LOG%" 2>&1
    git tag -f "%TAG%" -m "Backup: V1 Substrate Candidate with Page Sequence Signature Bridge (13th bridge)" >> "%LOG%" 2>&1

    echo Pushing branch... >> "%LOG%"
    git push -u origin "%BRANCH%" --force >> "%LOG%" 2>&1
    echo Push branch exit code: !errorlevel! >> "%LOG%"

    echo Pushing tag... >> "%LOG%"
    git push origin "%TAG%" --force >> "%LOG%" 2>&1
    echo Push tag exit code: !errorlevel! >> "%LOG%"

    echo Verifying remote... >> "%LOG%"
    git ls-remote origin "%BRANCH%" >> "%LOG%" 2>&1
    git ls-remote origin "refs/tags/%TAG%" >> "%LOG%" 2>&1

    echo ============================================ >> "%LOG%"
    echo DONE >> "%LOG%"
    echo %date% %time% >> "%LOG%"
)

echo.
echo Backup script finished. See _backup_log.txt for details.
echo Press any key to close...
pause >nul
