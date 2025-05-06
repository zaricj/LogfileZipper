@echo off
setlocal enabledelayedexpansion

:: Set the directory containing log files
set "LOG_DIR=\\nesnas01\ebd-archiv\logs-nc01"
echo Using directory: %LOG_DIR%

:: Calculate date 3 months ago
for /f "tokens=1-3 delims=/" %%a in ('echo %date%') do (
    set /a month=1%%b-100
    set /a year=%%c
    
    :: Subtract 3 months
    set /a month-=3
    if !month! leq 0 (
        set /a month+=12
        set /a year-=1
    )
    
    :: Pad month with leading zero if needed
    if !month! lss 10 set "month=0!month!"
    
    set "cutoff_date=!year!!month!"
)
echo Excluding files newer than: !cutoff_date!

:: Change to the log directory
cd /d "%LOG_DIR%" || (
    echo Failed to change to directory: %LOG_DIR%
    exit /b 1
)

:: Process each subdirectory
for /d %%D in (*) do (
    pushd "%%D"
    
    :: Check if there are any log files in this subdirectory
    dir /b *.log >nul 2>&1
    if not errorlevel 1 (
        echo Processing directory: %%D
        
        :: Create a temporary file listing eligible log files
        >"%TEMP%\eligible_files.txt" (
            :: Modified to handle any year in 2020s
            for /f "tokens=1,2,*" %%A in ('dir /b /tw 20??_??_*.log 2^>nul') do (
                :: Extract the year and month from filename (YYYY_MM_*)
                for /f "tokens=1,2 delims=_" %%X in ("%%A") do (
                    set "file_date=%%X%%Y"
                    if !file_date! gtr !cutoff_date! echo %%A
                )
            )
        )
        
        :: Extract unique year_month combinations from eligible files
        for /f "tokens=1,2 delims=_" %%A in ('type "%TEMP%\eligible_files.txt"') do (
            set "year_month=%%A_%%B"
			set "year_month_archive=%%A-%%B"
            
            :: Skip if archive already exists
            if not exist "!year_month_archive!.7z" (
                7z a -t7z "!year_month_archive!.7z" "!year_month!_*.log" -mx7 -mmt -sdel >nul
                
                if errorlevel 1 (
                    echo Failed to create archive: !year_month_archive!.7z
                ) 
            ) else (
                echo Archive already exists: !year_month_archive!.7z
            )
        )
        if errorlevel 0 (
                    echo Successfully created archive: !year_month_archive!.7z
                )
        
        del "%TEMP%\eligible_files.txt" 2>nul
    ) else (
        echo No log files found in directory: %%D
    )
    
    popd
)
echo Processing complete
endlocal
