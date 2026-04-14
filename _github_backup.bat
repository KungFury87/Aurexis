@echo off
setlocal enabledelayedexpansion

REM ── Aurexis Core GitHub Backup Script ──
REM Pushes current repo state to a removable backup branch + tag
REM Final Package Handoff Hardening — Release-Hardened V1 Substrate Candidate (51 bridges, 61 runners)

set "REPO_DIR=%~dp0"
set "BRANCH=backup/v1-substrate-candidate-20260413-193001"
set "TAG=backup-v1-substrate-candidate-20260413-193001"
set "LOG=%REPO_DIR%_backup_log.txt"
set "GCM_GITHUBAUTHMODE=device"

echo ============================================ > "%LOG%"
echo Aurexis Core GitHub Backup >> "%LOG%"
echo Final Package Handoff Hardening — V1 Substrate Candidate — 51 bridges >> "%LOG%"
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
    git commit -m "Final Package Handoff Hardening — V1 Substrate Candidate — 51 bridges, 6358 assertions, 61 runners, 67 source modules, handoff-ready" >> "%LOG%" 2>&1

    REM Create backup branch
    echo Creating branch %BRANCH%... >> "%LOG%"
    git checkout -B "%BRANCH%" >> "%LOG%" 2>&1

    REM Create tag
    echo Creating tag %TAG%... >> "%LOG%"
    git tag -f "%TAG%" -m "Backup: Final Package Handoff Hardening — V1 Substrate Candidate — 51 bridges, 6358 assertions, 61 runners, 67 source modules, 9 branches, handoff-ready" >> "%LOG%" 2>&1

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
    git commit -m "Final Package Handoff Hardening — V1 Substrate Candidate — 51 bridges, 6358 assertions, 61 runners, 67 source modules, handoff-ready" >> "%LOG%" 2>&1
    git checkout -B "%BRANCH%" >> "%LOG%" 2>&1
    git tag -f "%TAG%" -m "Backup: Final Package Handoff Hardening — V1 Substrate Candidate — 51 bridges, 6358 assertions, 61 runners, 67 source modules, 9 branches, handoff-ready" >> "%LOG%" 2>&1

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
