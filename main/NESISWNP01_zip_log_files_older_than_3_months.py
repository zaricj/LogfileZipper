import os
import re
import zipfile
import logging
import time
import calendar
import sys
from tqdm import tqdm
from collections import defaultdict
from datetime import datetime, timedelta

# Get directory where the script is currently located
script_dir = os.path.dirname(os.path.abspath(__file__))

# ========== Logging Configuration ========== #
log_dir = os.path.join(script_dir, "logs")
log_file = os.path.join(log_dir, "NESISWNP01_3_months_old_logs_zip_history.log")

# Create the directory if it doesn't exist
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    # print(f"Log folder couldn't be found, creating new one under the following path: '{log_dir}'")

# Configure logging to write to a .log file and console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    handlers=[
                        logging.FileHandler(log_file),  # Logs to a file
                    ])

logger = logging.getLogger(__name__)

logger.info(f"Script started in current working directory: {script_dir}")

# ========== END Logging Configuration END ========== #

LOGS_TO_ZIP_DIR: str = r"Y:\logs-wn01"

# ============= Path Configuration ========== #
try:
    logs_root_directory = LOGS_TO_ZIP_DIR
    if not os.path.exists(logs_root_directory):
        logger.error(f"Directory '{logs_root_directory}' does not exist or is not accessible. Please check the path.")
        logger.error("Exiting the program...")
        raise FileNotFoundError
except FileNotFoundError:
    sys.exit(1)
# ============= END Path Configuration END ========== #

# ========== Function Definitions ========== #

def get_cutoff_date():
    """Calculate the cutoff date (3 months ago) and adjust it to the last day of that month."""
    current_date = datetime.now()
    three_months_ago = current_date - timedelta(days=90)

    # Get last day of the month for the computed cutoff month
    last_day = calendar.monthrange(three_months_ago.year, three_months_ago.month)[1]

    # Set the cutoff date to the last day of that month
    cutoff_date = datetime(three_months_ago.year, three_months_ago.month, last_day)
    return cutoff_date  # Keep it as datetime for comparison


def is_file_older_than_cutoff(filename, cutoff_date):
    """Check if file is older than the cutoff date based on filename."""
    # Extract date from filename (assumes format starts with yyyy_mm_dd)
    date_str = filename[:10]  # Extract yyyy_mm_dd part
    try:
        file_date = datetime.strptime(date_str, "%Y_%m_%d")
        return file_date <= cutoff_date
    except ValueError:
        # If filename doesn't have proper date format, skip it
        return False


def group_log_files_by_month(root_directory, subdirectory=None):
    """Group log files by year-month from specified directory, only if older than 3 months."""
    try:
        base_path = root_directory if subdirectory is None else os.path.join(root_directory, subdirectory)
        files = os.listdir(base_path)
    except OSError as e:
        logger.error(f"Error accessing the directory: {e}")
        return {}, None
    
    logger.info(f"Processing files in {base_path}...")
    cutoff_date = get_cutoff_date()
    
    # Filter log files matching yyyy_mm_dd pattern and older than 3 months
    log_files = [f for f in files if os.path.isfile(os.path.join(base_path, f)) and 
                re.match(r"^\d{4}_\d{2}_\d{2}.*\.log$", f) and
                is_file_older_than_cutoff(f, cutoff_date)]
    
    # Group files by year-month
    monthly_files = defaultdict(list)
    for log_file in log_files:
        # Extract yyyy_mm from the filename
        year_month = log_file[:7]  # Takes "yyyy_mm" part
        # Convert to yyyy-mm format for zip naming
        zip_key = year_month.replace("_", "-")
        monthly_files[zip_key].append(log_file)
    
    return monthly_files, base_path


def zip_monthly_files(monthly_files, base_path, log_files_to_cleanup, subdirectory=None):
    """Create zip archives for each month's log files."""
    location = "root directory" if subdirectory is None else f"subdirectory '{subdirectory}'"
    
    if not monthly_files:
        logger.info(f"No files older than 3 months found in {location}")
        return log_files_to_cleanup 
    
    # Create a zip file for each month
    for year_month, files in tqdm(monthly_files.items(), desc=f"Creating monthly archive in {location}"):
        # Create zip filename in format yyyy-mm.zip
        zip_filename = f"{year_month}.zip"
        zip_path = os.path.join(base_path, zip_filename)
        
        # Create the zip file
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_BZIP2) as zipf:
            for log_file in tqdm(files, desc=f"Adding files to zip {zip_filename} in {base_path}"):
                file_path = os.path.join(base_path, log_file)
                # Store file in the zip with its original name
                zipf.write(file_path, arcname=log_file)
                # Add file to dictionary for later cleanup after zipping has finished
                log_files_to_cleanup[year_month].append(file_path)

        logger.info(f"Created {zip_filename} with {len(files)} log files")
    
    # Return statement moved OUTSIDE the loop - this was the bug!
    return log_files_to_cleanup

def process_directory(root_directory):
    """Process the root directory and all its subdirectories."""
    
    # Variables that contains log files to cleanup:
    log_files_to_cleanup = defaultdict(list)
    
    try:
        logger.info("============================================")
        logger.info(f"Starting log file archiving process in {root_directory}")
        logger.info("============================================")
        cutoff_date = get_cutoff_date()
        logger.info(f"Cutoff date set to: {cutoff_date.strftime('%Y.%m.%d')}")  
        logger.info(f"Archiving files older than: {cutoff_date.strftime('%Y-%m-%d')} (3 months ago)")

        # Process log files in the root directory
        monthly_files, base_path = group_log_files_by_month(root_directory)
        if monthly_files:
            log_files_to_cleanup = zip_monthly_files(monthly_files, base_path, log_files_to_cleanup)
            if log_files_to_cleanup:
                log_files_cleanup(log_files_to_cleanup)
                log_files_to_cleanup = defaultdict(list)  # Reset after cleanup
        else:
            logger.info("============================================")
            logger.info("No log files older than 3 months found in the root directory")

        # Get all subdirectories
        subdirs = [d for d in os.listdir(root_directory) if os.path.isdir(os.path.join(root_directory, d))]
        # Process each subdirectory
        for subdir in subdirs:
            monthly_files, base_path = group_log_files_by_month(root_directory, subdir)
            if monthly_files:
                log_files_to_cleanup = zip_monthly_files(monthly_files, base_path, log_files_to_cleanup, subdir)
                if log_files_to_cleanup:
                    log_files_cleanup(log_files_to_cleanup)
                    log_files_to_cleanup = defaultdict(list)  # Reset after cleanup
            else:
                logger.info(f"No log files older than 3 months found in the sub directory: {subdir}")
                
    except (FileNotFoundError, FileExistsError, OSError) as e:
        logger.error(f"Error accessing the directory: Exception: '{type(e).__name__}'. Error: '{e}'")
        print((f"Error accessing the directory: Exception: '{type(e).__name__}'. Error: '{e}'"))


def log_files_cleanup(log_files_to_cleanup):
    logger.info("============================================")
    logger.info("Starting process to cleanup zipped log files")
    logger.info("============================================")
    logger.info("Checking if there are any log files to be cleaned up.")
    if log_files_to_cleanup:
        logger.info("Found log files to clean up for the following months:")
        for key in log_files_to_cleanup:
            logger.info(f"{key}")
        for key, file_list in log_files_to_cleanup.items():
            logger.info(f"Starting to clean up log files for '{key}'...")
            for file_path in tqdm(file_list, desc="Deleting log files..."):
                try:
                    os.unlink(file_path)
                    logger.info(f"Deleted log file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
            logger.info("==================================================")
            logger.info(f"All log files have been DELETED for month '{key}'")
            logger.info("==================================================")
    else:
        logger.info("Nothing to cleanup up, as no log files have been zipped.")


if __name__ == "__main__":
    start_time = time.time()
    process_directory(logs_root_directory)
    end_time = time.time()
    logger.info(f"Archiving process completed in {end_time - start_time:.2f} seconds")
