from pathlib import Path
from tqdm import tqdm
import time
import re
import zipfile
import logging
import os

# Get directory where the script is currently located
script_dir = os.path.dirname(os.path.abspath(__file__))
print(script_dir)

log_dir = os.path.join(script_dir, "Log")
log_file = os.path.join(log_dir, "zipping_history.log")
 
# Create the directory if it doesn't exist
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    print(f"\nLog folder couldn't be found, create new one under the following path: '{log_dir}'")
else:
    print(f"\nLog folder initialized under the path: '{log_dir}'")

# Configure logging to write to a .log file and console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    handlers=[
                        logging.FileHandler(log_file),  # Logs to a file
                    ])
logger = logging.getLogger(__name__)


# logs_dir = "//nesnas01/ebd-archiv/logs"
# output_dir = "//nesnas01/ebd-archiv/logs"  # Zipfiles output

msg = r"""
 __    __ _ _ _ _                                        
/ / /\ \ (_) | | | _____  _ __ ___  _ __ ___   ___ _ __  
\ \/  \/ / | | | |/ / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \ 
 \  /\  /| | | |   < (_) | | | | | | | | | | |  __/ | | |
  \/  \/ |_|_|_|_|\_\___/|_| |_| |_|_| |_| |_|\___|_| |_|
                                                         
"Ein CLI-Tool zum Komprimieren von Logdateien im ZIP-Format. 
Unterstützt werden nur Logdateien, die das Datum im Format yyyy_mm_dd im Dateinamen enthalten. 
Beispiele für unterstützte Logs: 2024_03_20_server.log, 2024_08_27.adminrequest.log, 2024_08_03_message.log. 
Die Logdateien werden nach dem Monat im Dateinamen gruppiert und für jeden Monat wird ein separates .zip-Archiv erstellt."    
"""

print(msg)

# --------- start CLI Prompts start --------- #

while True:
    # Prompt user for the logs directory path
    logs_dir = input("Enter path that contains the logs for zipping or 'exit' to close the program:\n>>> ").strip()
    
    # Check if user wants to exit
    if logs_dir.lower() == "exit":
        print("Closing program, bye!")
        exit()

    # Validate the logs directory path
    if Path(logs_dir).is_dir():
        files = [file for file in Path(logs_dir).iterdir() if file.is_file() and file.suffix == ".log"]
        print(f"Entered path for log files: {logs_dir} (Found {len(files)} log files)")
        logger.info(f"Entered path for log files: {logs_dir} (Found {len(files)} log files)")
        
        if len(files) == 0:
            print(f"Entered path {logs_dir} has no log files, please select a different path.")
            logger.info(f"Entered path {logs_dir} has no log files, please select a different path.")
            continue
    
    else:
        print("Not a valid path! Please try again.")
        continue  # Retry asking for logs directory

    # Prompt user for the output directory path
    output_dir = input("Enter path where to save zipped archives (Enter 'same' to use the previously entered path or 'exit' to close the program):\n>>> ").strip()

    # Check if user wants to exit
    if output_dir.lower() == "exit":
        print("Closing program, bye!")
        exit()

    # Check if output path is 'same' or a new path
    if output_dir.lower() == "same":
        output_dir = logs_dir
        print(f"Entered path for zipped archives: {output_dir}")
        logger.info(f"Entered path for zipped archives: {output_dir}")
        
    elif not Path(output_dir).exists():
        create_folder = input("Path doesn't exist, do you want to create it? (y/n):\n>>> ")
        if create_folder.lower() == "y":
            try:
                Path(output_dir).mkdir(parents=True, exist_ok=False)
                print(f"Created folder {output_dir} for zipped archives.")
                logger.info(f"Created folder {output_dir} for zipped archives.")
            except Exception as e:
                print(f"Error creating directory: {e}")
                continue  # Retry if creation fails
        elif create_folder.lower() == "n":
            print("Restarting program, please enter a valid path.")
            continue  # Retry asking for a valid path
    
    elif Path(output_dir).is_dir():
        print(f"Entered path for zipped archives: {output_dir}")
        logger.info(f"Entered path for zipped archives: {output_dir}")
    else:
        print("Not a valid path. Please try again.")
        continue  # Retry asking for a valid path
    
    # Prompt user if deletion of log files after zipping them should be done
    while True:
        deleted_zipped_logs = input("Do you want to delete the log files after zipping them? (y/n):\n>>> ").strip()

        # Check if user wants to exit
        if deleted_zipped_logs.lower() == "exit":
            print("Closing program, bye!")
            exit()
            
        if deleted_zipped_logs.lower() == "y":
            print("Log files will be deleted after zipping completes.")
            logger.info("Log files will be deleted after zipping completes.")
            log_files_delete_flag = True
            break
        elif deleted_zipped_logs.lower() == "n":
            print("Log files will not be deleted after zipping completes.")
            logger.info("Log files will not be deleted after zipping completes.")
            log_files_delete_flag = False
            break
        else:
            print("Not a valid command. Please try again.")

    # If all inputs are valid and processed, break out of the main loop
    break

# --------- end CLI Prompts end --------- #

# List to store all log files
files = []

# Collect all log files in the directory
files = [file for file in Path(logs_dir).iterdir() if file.is_file() and file.suffix == ".log"]

# Dictionary to group files by (year, month)
files_grouped_by_month = {}

# Regex pattern to match the date in the format YYYY_MM_DD
pattern = r"(\d{4})_(\d{2})_(\d{2})_?.*\.log"

# Group files by (year, month)
for f in files:
    file_string = f.name  #  Get filename part

    # RegEx re.match to find the date in the filename
    match = re.match(pattern, file_string)

    if match:
        year, month, _ = match.groups()

        # Group files by (year, month)
        key = (year, month)
        files_grouped_by_month.setdefault(key, []).append(f)
        
if not files_grouped_by_month:
    no_logs_msg = "Found no log files to zip... Finishing up..."
    logger.info("Found no log files to zip... Finishing up...")
    print(f"{no_logs_msg}")
    print({len(no_logs_msg * "-")})
    print("Program is closing in 5 seconds...")
    
    # Countdown timer
    for counter in range(5, 0, -1):
        print(counter)
        time.sleep(1)
        
    exit() # TODO Fix NameError Exception
        
else:

   # Zip the files grouped by (year, month)
    for (year, month), group_files in files_grouped_by_month.items():
        zip_filename = f"{year}-{month}.zip"
        zip_path = Path(output_dir) / zip_filename

      # Create the Zip file and add the grouped files to it
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_BZIP2) as zipf:
            for file in tqdm(group_files, "Zipping files: "):
                zipf.write(str(file), arcname=file.name)
                if log_files_delete_flag:
                    Path.unlink(file) # Deletes log files after zipping them
                else:
                    continue
            
        print(f"Zipping complete - Archive '{zip_filename}' created in path '{Path(output_dir)}' with {len(group_files)} log files.")
        logger.info(f"Zipping complete - Archive '{zip_filename}' created in path '{Path(output_dir)}' with {len(group_files)} log files.")
        
        if log_files_delete_flag:
            print(f"Cleaning up - Deleted {len(group_files)} log files successfully.")
            logger.info(f"Cleaning up - Deleted {len(group_files)} log files successfully.")
            