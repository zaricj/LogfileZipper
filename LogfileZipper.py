from pathlib import Path
from tqdm import tqdm
import time
import re
import py7zr
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
    print(f"Log folder couldn't be found, create new one under the following path: '{log_dir}'")
else:
    print(f"Log folder initialized under the path: '{log_dir}'")

# Configure logging to write to a .log file and console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    handlers=[
                        logging.FileHandler(log_file),  # Logs to a file
                        logging.StreamHandler()  # Logs to the console
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
                                                         
Log Dateien zipper im 7z format. Nur log Dateien mit yyyy-mm-dd im Namen unterstuzt.
Beispiel logs: 2024_03_20_server, 2024_08_27.adminrequest.log, 2024_08_03_message.log ...                                                      
"""

print(msg)

print("Geben Sie den Pfad ein, der die Logs zum Zippen enthält oder 'exit', um das Programm zu schließen.")

while True:
    # Prompt user for the logs directory path
    logs_dir = input("Pfad, der die Logs zum Zippen enthält: ").strip()

    # Check if user wants to exit
    if logs_dir.lower() == "exit":
        print("Programm wird beendet.")
        exit()

    if Path(logs_dir).is_dir():
        print(f"Eingegebener Pfad für Logdateien: {logs_dir}")
    else:
        print("Kein gültiger Pfad. Versuchen Sie es erneut.")
        continue  # Retry asking for logs directory

    # Prompt user for the output directory path
    output_dir = input("Geben Sie den Ausgabepfad für gezippte Archive ein\n(Geben Sie 'same' ein, um den zuvor eingegebenen Pfad zu verwenden, oder 'exit' zum Beenden): ").strip()

    # Check if user wants to exit
    if output_dir.lower() == "exit":
        print("Programm wird beendet.")
        exit()

    # Check if output path is 'same' or a new path
    if output_dir.lower() == "same":
        output_dir = logs_dir
        print(f"Eingegebener Pfad für Zip-Archives: {output_dir}")
        break
    elif Path(output_dir).is_dir():
        print(f"Eingegebener Pfad für Zip-Archives: {output_dir}")
        break
    else:
        print("Kein gültiger Pfad. Versuchen Sie es erneut.")
        

# Ensure the output directory exists
Path(output_dir).mkdir(parents=True, exist_ok=True)

# List to store all the files
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
    no_logs_msg = "Keine Protokolldateien zum Zippen gefunden..."
    logger.info("Found no log files to zip. Finishing up...")
    print(f"{no_logs_msg}")
    print({len(no_logs_msg * "-")})
    print("Program schließt sich in 5 sekunden...")
    
    # Countdown timer
    for counter in range(5, 0, -1):
        print(counter)
        time.sleep(1)
        
    exit() # TODO Fix NameError Exception
        
else:

   # Zip the files grouped by (year, month)
   for (year, month), group_files in files_grouped_by_month.items():
      zip_filename = f"{year}-{month}.7z"
      zip_path = Path(output_dir) / zip_filename

      # Create the Zip file and add the grouped files to it
      with py7zr.SevenZipFile(zip_path, "w") as zipf:
         for file in tqdm(group_files, "Zipping files: "):
            zipf.write(str(file), arcname=file.name)
            Path.unlink(file) # deletes log files after zipping them
            
      print(f"Zip-Datei erstellt: {zip_path} mit {len(group_files)} Dateien.")
      print(f"Löschen von {len(group_files)} log Dateien erfolgreich.")
      logger.info(f"Created zip file: {zip_path} with {len(group_files)} files.")
      logger.info(f"Cleaning up... deleted {len(group_files)} log files.")
    

