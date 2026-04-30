@echo off
cd /d "D:\CLARIO"

echo ============================================================
echo  Clario — Push to GitHub
echo ============================================================
echo.

:: Check if git is initialized
if not exist ".git" (
    echo [1/5] Initializing git repository...
    git init
) else (
    echo [1/5] Git already initialized.
)

:: Set remote (safe to run even if already set)
echo [2/5] Setting remote origin...
git remote remove origin 2>nul
git remote add origin https://github.com/Mohammedsami001/Clario.git

:: Stage all files
echo [3/5] Staging all files...
git add .

:: Show what will be committed
echo.
echo Files to be committed:
git status --short
echo.

:: Safety check — confirm .env is ignored
git check-ignore -q backend/.env && (
    echo [OK] backend/.env is gitignored - your API key is safe.
) || (
    echo [WARNING] backend/.env might not be ignored! Check your .gitignore.
    pause
)

:: Commit
echo [4/5] Committing...
git commit -m "feat: initial Clario backend — full pipeline MVP"

:: Push
echo [5/5] Pushing to GitHub...
git branch -M main
git push -u origin main

if %errorlevel% == 0 (
    echo.
    echo ============================================================
    echo  SUCCESS! Code pushed to:
    echo  https://github.com/Mohammedsami001/Clario
    echo ============================================================
) else (
    echo.
    echo Push failed. Trying with --allow-unrelated-histories...
    git pull origin main --allow-unrelated-histories --no-edit
    git push -u origin main
)

echo.
pause
