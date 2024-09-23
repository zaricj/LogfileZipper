
# LogfileZipper
This Python script is a command line tool (CLI) for compressing log files in zip format. It only supports log files whose file names contain a date in the format `yyyy_mm_dd`, e.g. `2024_03_20_server.log`. The script groups the log files according to the month in the file name and creates a separate `zip` archive for each month.

## Alternative GUI Version
The GUI version is more flexible and dynamic, it uses RegEx patterns to search for log filename patterns and groups them by the pattern.

## Functionality

- The script searches a specified directory for log files and compresses them into `.7z` archives.
- The log files are grouped according to the date in the file name (year and month).
- An archive is created for each month containing all the associated log files.
- It is possible to delete the original log files after compression.

## Prerequisites

- Python 3.6 or higher
- Dependencies: `tqdm` (for the progress bar)

## Installation

1. install Python 3.6 or higher.
2. install Python package `tqdm`:

   ```bash
   pip install tqdm
   ```

## Usage

1. execute the script in the terminal/CMD:
   ```bash
   python LogfileZipper.py
   ```

2. follow the prompts:
   - **Logs directory**: Path of the directory containing the log files to be compressed.
   - **Target directory**: Path where the compressed archives should be saved (can be the same directory as the logs directory).
   - Delete log files**: Decision whether the original log files should be deleted after compression.

3. the script displays the progress of compression and logging in the console. The log files are saved under `Log/zipping_history.log`.

## Examples of supported log files

- 2024_03_20_server.log
- `2024_08_27.adminrequest.log`
- `2024_08_03_message.log`

## Logging

The script creates a log directory (`log`) and saves all activities in the file `zipping_history.log`. Both errors and information on the execution of the script are logged.

## Windows Executable Binary

A GUI version of the script is available under the releases.

Direct download link: [Download LogfileZipper](https://git.de.geis-group.net/-/project/646/uploads/421d41b3658aeab2280b28933334f031/LogfileZipperGUI.7z)

## Troubleshooting

- Make sure that the directory paths entered exist and are valid.
- Check the permissions to create files and directories.
- If the script does not find any log files, check whether the file names correspond to the format `yyyyy_mm_dd`.

## Screenshots and GIFs

### CLI screenshot

![CLI](docs/images/CLI_Showcase.png)

### GUI Screenshot

![GUI](docs/images/GUI_Showcase.png)

### GUI Demo GIF

![Demo](docs/images/LogArchiverDemo.gif)
