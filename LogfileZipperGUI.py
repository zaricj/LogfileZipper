from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QTextEdit, QProgressBar, QStatusBar, QCheckBox,
                             QFileDialog, QMessageBox, QSizePolicy, QTreeView, QFileSystemModel, QDateTimeEdit)
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QDropEvent
from PySide6.QtCore import QThread, Signal, QObject, QDir, QFile, QTextStream, QSettings, QDate
from pathlib import Path
import re
import zipfile
import os
import sys
import time
from datetime import datetime
from collections import defaultdict

# Directory where the script is located
basedir = os.path.dirname(__file__)

class Worker(QObject):
    progress_updated = Signal(int)
    log_message = Signal(str)
    finished = Signal()
    show_message = Signal(str, str)

    def __init__(self, parent, input_folder:str, output_folder:str, patterns:list, compression_method:str, delete_logfiles_after_zipping:bool, date_filter_state:bool, zip_files_older_than_date:datetime):
        super().__init__()
        self.parent = parent
        self.input_folder: str = input_folder
        self.output_folder: str = output_folder
        self.pattern: list = patterns
        self.compression_method_text: str = compression_method  
        self.delete_logfiles_checkbox: bool = delete_logfiles_after_zipping
        self.date_filter_state: bool = date_filter_state
        self.zip_files_older_than_date: str = zip_files_older_than_date
        
        if compression_method  == "zlib (Fast)":
            self.compression_method = zipfile.ZIP_DEFLATED
        elif compression_method  == "bz2 (Good)":
            self.compression_method = zipfile.ZIP_BZIP2
        elif compression_method  == "lzma (Highest)":
            self.compression_method = zipfile.ZIP_LZMA
    
    def zip_files_no_date_filter(self, input_folder:str, output_folder:str, patterns:list) -> None:
        try:
            start = time.process_time()
            counter = 0 # Counter to display compressing archive 1 out of n
            for pattern in patterns:
                counter += 1 # Updating the counter
                regex = f"^{re.escape(pattern).replace('\\*', '.*')}$"
                
                # Only .log files - Change in the future maybe to any filetype = remove f.endswith(".log"), pattern must then end like this "*.<some_filetype> e.x. (*.xlsx, *.txt, *.mp3 etc...)"
                matching_files = [f for f in os.listdir(input_folder) if f.endswith(".log") and re.match(regex, f)] 
                total_files = len(matching_files)
                
                if matching_files:
                    # Print processing message
                    self.log_message.emit(f"Starting to compress log files with compression method: {self.compression_method_text}")
                    creating_archive_message = f"Creating archive {pattern.replace('*', '')}.zip ({counter}/{len(patterns)})"
                    self.log_message.emit(len(creating_archive_message) * "-")
                    self.log_message.emit(creating_archive_message)
                    self.log_message.emit(len(creating_archive_message) * "-")
                    # Continue processing
                    zip_filename = f"{pattern.replace('*', '')}.zip"
                    zip_path = os.path.join(output_folder, zip_filename)
                    self.log_message.emit("Starting zipping of log files...")
                    with zipfile.ZipFile(zip_path, "w", compression=self.compression_method) as zipf:
                        for index, file in enumerate(matching_files):
                            self.log_message.emit(f"Zipping file {file}")
                            file_path = os.path.join(input_folder, file)
                            zipf.write(file_path, arcname=file)
                            if self.delete_logfiles_checkbox:
                                os.unlink(file_path) # Deletes zipped log files
                            progress = int((index + 1) / total_files * 100)
                            self.progress_updated.emit(progress)
                    
                    elapsed = time.process_time() - start
                    
                    if self.delete_logfiles_checkbox:
                        task_complete_message = f"\nTask completed - Created archive '{zip_filename}' with {len(matching_files)} files.\nCleaning up - Deleted {len(matching_files)} log files that were zipped.\nElapsed time: {round(elapsed, 2)} seconds."
                        self.log_message.emit(task_complete_message)
                    else:
                        task_complete_message = f"\nTask completed - Created archive '{zip_filename}' with {len(matching_files)} files.\nElapsed time: {round(elapsed, 2)} seconds."
                        self.log_message.emit(task_complete_message)
                else:
                    self.log_message.emit(f"No files found matching pattern(s): {pattern}")

        except Exception as ex:
            message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
            self.log_message.emit(message)
            self.show_message.emit("An exception occurred", message)  

            
    def zip_files_with_date_filter(self, input_folder:str, output_folder:str, zip_files_older_than_date:datetime) -> None:
        try:
            start = time.process_time()
            counter = 0 # Counter to display compressing archive 1 out of n
            files_to_zip: dict[str, list[str]] = defaultdict(list)

            # Only .log files - Change in the future maybe to any filetype = remove f.endswith(".log"), pattern must then end like this "*.<some_filetype> e.x. (*.xlsx, *.txt, *.mp3 etc...)"
            matching_files = [f for f in os.listdir(input_folder) if f.endswith(".log")] 
            
            for file in matching_files:
                file_path = os.path.join(input_folder, file)
                creation_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                key = creation_time.strftime("%Y_%m")  # e.g. '2025_03'
                
                if creation_time < zip_files_older_than_date: # Add files to dictionary if older than the date
                    files_to_zip[key].append(file)
                
                
            if files_to_zip:
                for key, values in files_to_zip.items():
                    total_files = sum(len(v) for v in files_to_zip.values())
                    files_processed = 0

                    counter += 1 # Updating the counter
                    zip_filename = f"{key}.zip"
                    # Print processing message
                    self.log_message.emit(f"Starting to compress log files with compression method: {self.compression_method_text}")
                    creating_archive_message = f"Creating archive {zip_filename} ({counter}/{len(files_to_zip.keys())})"
                    self.log_message.emit(len(creating_archive_message) * "-")
                    self.log_message.emit(creating_archive_message)
                    self.log_message.emit(len(creating_archive_message) * "-")
                    # Continue processing
                    zip_path = os.path.join(output_folder, zip_filename)
                    self.log_message.emit("Starting zipping of log files...")
                    with zipfile.ZipFile(zip_path, "w", compression=self.compression_method) as zipf:
                        for file in values:
                            self.log_message.emit(f"Zipping file {file}")
                            files_processed += 1
                            file_path = os.path.join(input_folder, file)
                            zipf.write(file_path, arcname=file)
                            if self.delete_logfiles_checkbox:
                                os.unlink(file_path) # Deletes zipped log files
                        progress = int((counter / len(files_to_zip.keys())) * 100)
                        self.progress_updated.emit(progress)

                    elapsed = time.process_time() - start

                    if self.delete_logfiles_checkbox:
                        task_complete_message = f"\nTask completed - Created archive '{zip_filename}' with {len(matching_files)} files.\nCleaning up - Deleted {files_processed} log files that were zipped\nElapsed time: {round(elapsed, 2)} seconds."
                        self.log_message.emit(task_complete_message)
                    else:
                        task_complete_message = f"\nTask completed - Created archive '{zip_filename}' with {files_processed} files.\nElapsed time: {round(elapsed, 2)} seconds."
                        self.log_message.emit(task_complete_message)
            else:
                self.log_message.emit("No matching files found.")
                        
        except Exception as ex:
            message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
            self.log_message.emit(message)
            self.show_message.emit("An exception occurred", message)  
            

    def run(self):
        try:
            if self.date_filter_state:
                self.zip_files_with_date_filter(self.input_folder, self.output_folder, self.zip_files_older_than_date)
            else:
                self.zip_files_no_date_filter(self.input_folder, self.output_folder, self.pattern)
                
            # Emit finished signal
            self.finished.emit()
            
        except Exception as ex:
            message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
            self.log_message.emit(message)
            self.show_message.emit("An exception occurred", message)  
            self.finished.emit()

class DraggableLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # Enable dropping on QLineEdit

    def dragEnterEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  # Accept the drag event
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  # Accept the drag move event
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            # Extract the file path from the drop event
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.setText(file_path)
            event.acceptProposedAction()  # Accept the drop event
        else:
            event.ignore()

class MainWindow(QMainWindow):
    progress_updated = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Logfile Zipper v1.1.0")
        self.setWindowIcon(QIcon(os.path.join("resources","_internal","icon","zipzap.ico")))
        self.setGeometry(500, 250, 800, 700)
        self.saveGeometry()
        
        # Settings to save current location of the windows on exit
        self.settings = QSettings("App","LogfileZipper")
        geometry = self.settings.value("geometry", bytes())
        self.restoreGeometry(geometry)
        
        # Current theme files to set as the main UI theme
        self.theme = os.path.join("resources","_internal","themes","default.qss")
        
        # Initialize the .qss Theme File on startup
        self.initialize_theme(self.theme)
        
        # Initialize the UI and it's layouts
        self.initUI()
        
        # Create the menu bar
        self.create_menu_bar()
    
    def initialize_theme(self, theme_file):
        try:
            file = QFile(theme_file)
            if file.open(QFile.ReadOnly | QFile.Text):
                stream = QTextStream(file)
                stylesheet = stream.readAll()
                self.setStyleSheet(stylesheet)
            file.close()
        except Exception as ex:
            message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
            QMessageBox.critical(self, "Theme load error", f"Failed to load theme:\n{message}")
        
    def initUI(self):
        
        # Signals and Slots
        self.progress_updated.connect(self.update_progress)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Input folder selection
        self.input_folder = QLineEdit()
        self.input_folder.setPlaceholderText("Choose a folder that contains .log files...")
        self.input_folder.textChanged.connect(self.update_log_files_count)
        input_folder_layout = QHBoxLayout()
        input_folder_layout.addWidget(self.input_folder)
        self.input_folder_button = QPushButton("Browse")
        self.input_folder_button.clicked.connect(self.browse_input_folder)
        input_folder_layout.addWidget(self.input_folder_button)
        layout.addWidget(QLabel("Input Folder:"))
        layout.addLayout(input_folder_layout)

        # Output folder selection
        self.output_folder = QLineEdit()
        self.output_folder.setPlaceholderText("Choose a folder where to save the zipped archives...")
        output_folder_layout = QHBoxLayout()
        output_folder_layout.addWidget(self.output_folder)
        self.output_folder_button = QPushButton("Browse")
        self.output_folder_button.clicked.connect(self.browse_output_folder)
        output_folder_layout.addWidget(self.output_folder_button)
        layout.addWidget(QLabel("Output Folder:"))
        layout.addLayout(output_folder_layout)
        
        
        # Input for log file patterns
        self.pattern_input = DraggableLineEdit()
        self.pattern_input.setPlaceholderText("Enter log file patterns (wildcard * is accepted) E.g. 2024_08*, info_message*")
        self.pattern_input.setClearButtonEnabled(True)
        layout.addWidget(QLabel("Log File Patterns (comma-separated):"))
        layout.addWidget(self.pattern_input)
        
        # Date Filter Layout
        date_filter_layout = QHBoxLayout()
        
        self.enable_date_filter_checkbox = QCheckBox("Enable Date Filter")
        self.enable_date_filter_checkbox.setChecked(False)
        self.enable_date_filter_checkbox.stateChanged.connect(self.enable_date_filter_state)
        self.zip_files_older_than_label = QLabel("Zip files older than the date (yyyy.mm.dd):")
        self.zip_files_older_than_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.zip_files_older_than = QDateTimeEdit(QDate.currentDate())
        self.zip_files_older_than.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.zip_files_older_than.setCalendarPopup(True)
        self.zip_files_older_than.setDisplayFormat("yyyy.MM.dd")
        self.zip_files_older_than.setDisabled(True)
        
        date_filter_layout.addWidget(self.enable_date_filter_checkbox)
        date_filter_layout.addWidget(self.zip_files_older_than_label)
        date_filter_layout.addWidget(self.zip_files_older_than)
        layout.addLayout(date_filter_layout)
        
        # Buttons Layout
        buttons_layout = QHBoxLayout()
        
        # Compression CombBox
        self.compression_method_combobox = QComboBox()
        compression_method_combobox_label = QLabel("Compression method:")
        self.compression_method_combobox.addItems(["zlib (Fast)", "bz2 (Good)", "lzma (Highest)"])
        self.compression_method_combobox.setCurrentText("bz2 (Good)")
        
        self.delete_logfiles_checkbox = QCheckBox("Delete log files after zipping?")

        buttons_layout.addWidget(compression_method_combobox_label)
        buttons_layout.addWidget(self.compression_method_combobox)
        buttons_layout.addWidget(self.delete_logfiles_checkbox)
        
        # Zip button
        self.zip_button = QPushButton("Start Zipping Log Files")
        self.zip_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.zip_button.clicked.connect(self.zip_log_files)
        buttons_layout.addWidget(self.zip_button)
        
        layout.addLayout(buttons_layout)

        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)
        
        # Statusbar Layout
        statusbar_layout = QHBoxLayout()
        
        self.logfiles_count_statusbar = QStatusBar()
        self.setStatusBar(self.logfiles_count_statusbar)
        self.logfiles_count_statusbar.setSizeGripEnabled(False)
        self.logfiles_count_statusbar.setStyleSheet("font-size: 16px; font-weight: bold; color: #11d957")
        statusbar_layout.addWidget(self.logfiles_count_statusbar)
        layout.addLayout(statusbar_layout)
        
        # Program output and Tree View
        program_output_and_treeview_layout = QHBoxLayout()

        # Left side: Program Output
        program_output_vertical_layout = QVBoxLayout()
        self.program_output_label = QLabel("Program Output:")
        self.program_output = QTextEdit()
        self.program_output.setReadOnly(True)
        program_output_vertical_layout.addWidget(self.program_output_label)
        program_output_vertical_layout.addWidget(self.program_output)

        # Right side: Tree View
        tree_view_vertical_layout = QVBoxLayout()
        self.tree_view_label = QLabel("Tree View:")
        self.tree_view = QTreeView(self)
        self.tree_view.setDragEnabled(True)  # Enable dragging
        tree_view_vertical_layout.addWidget(self.tree_view_label)
        tree_view_vertical_layout.addWidget(self.tree_view)

        # Add both vertical layouts to the horizontal layout
        program_output_and_treeview_layout.addLayout(program_output_vertical_layout)
        program_output_and_treeview_layout.addLayout(tree_view_vertical_layout)

        # Add the horizontal layout to the main vertical layout
        layout.addLayout(program_output_and_treeview_layout)

        # Set up the file system model
        self.file_system_model = QFileSystemModel(self)
        self.file_system_model.setRootPath("")  # Set root path to the filesystem's root
        self.file_system_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)  # Show all dirs and files

        # Set the model to the tree view
        self.tree_view.setModel(self.file_system_model)
        self.tree_view.setRootIndex(self.file_system_model.index(""))  # Set root index to the user's home directory

        # Optional: Customize the view
        self.tree_view.setColumnWidth(0, 250)  # Adjust column width
        self.tree_view.setHeaderHidden(False)   # Show the header
        self.tree_view.setSortingEnabled(True)  # Enable sorting
        
        # Combobox signal state changed
        self.compression_method_combobox.currentTextChanged.connect(self.get_compression_method)
    
    def closeEvent(self, event: QCloseEvent):
        reply = QMessageBox.question(self, "Exit Program", "Are you sure you want to exit the program?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        geometry = self.saveGeometry()
        self.settings.setValue("geometry", geometry)
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            
    def enable_date_filter_state(self):
        if self.enable_date_filter_checkbox.isChecked():
            self.zip_files_older_than.setDisabled(False)
            self.pattern_input.setDisabled(True)
            if self.pattern_input.text():
                self.pattern_input.clear()
        else:
            self.zip_files_older_than.setDisabled(True)
            self.pattern_input.setDisabled(False)
            
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        # File Menu
        file_menu = menu_bar.addMenu("&File")
        clear_action = QAction("Clear Output", self)
        clear_action.setStatusTip("Clear the output")
        clear_action.triggered.connect(self.clear_output)
        file_menu.addAction(clear_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Open Menu
        open_menu = menu_bar.addMenu("&Open")
        open_input_action = QAction("Open Input Folder", self)
        open_input_action.setStatusTip("Opens the log files input folder")
        open_input_action.triggered.connect(self.open_input_folder)
        open_menu.addAction(open_input_action)
        open_output_action = QAction("Open Output Folder", self)
        open_output_action.setStatusTip("Opens the zipped archives output folder")
        open_output_action.triggered.connect(self.open_output_folder)
        open_menu.addAction(open_output_action)
    
    # ====== Functions Start ====== #
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def clear_output(self):
        self.program_output.clear()
        
    def get_compression_method(self):
        combobox_text = self.compression_method_combobox.currentText()
        if combobox_text == "zlib (Fast)":
            desc_txt = """
        Pros:
            1. Fast compression and decompression.
            2. Provides a good balance between compression speed and compression ratio.
        Cons:
            1. The compression ratio is generally lower than bz2 and lzma.
            
Best for: General use cases where compatibility, speed, and reasonable compression are needed (e.g., web transfers, archives)."""
        
            self.program_output.setText(f"Selected compression method: {combobox_text} - Description:\n{desc_txt}")
        
        elif combobox_text == "bz2 (Good)":
            desc_txt = """
        Pros:
            1. Higher compression ratio than zlib for most files.
            2. Good decompression speed.
        Cons:
            1. Slower compression speed compared to zlib.
            
Best for: Situations where higher compression is desired and compression speed is less of a concern (e.g., backups, log files)."""

            self.program_output.setText(f"Selected compression method: {combobox_text} - Description:\n{desc_txt}")
        
        elif  combobox_text == "lzma (Highest)":
            desc_txt = """
        Pros:
            1. Achieves the highest compression ratio among the three methods.
            2. Good choice for very large files or when maximum compression is necessary.
        Cons:
            1. Slower compression and decompression speed.
            2. Consumes more memory during compression.
            
Best for: Cases where maximum compression is essential, and speed or memory usage is not critical (e.g., distributing software packages, compressing large datasets)."""
            
            self.program_output.setText(f"Selected compression method: {combobox_text} - Description:\n{desc_txt}")
            
    # Open Log files input folder 
    def open_input_folder(self):
        directory_path = self.input_folder.text()
        
        if os.path.exists(directory_path):
            try:
                os.startfile(directory_path)
            except Exception as ex:
                message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
                QMessageBox.critical(self, "An exception occurred", message)
        else:
            QMessageBox.warning(self, "Path Error", f"Path does not exist or is not a valid path:\n{directory_path}")
    
    
    # Open Zipped Archive output folder
    def open_output_folder(self):
        directory_path = self.output_folder.text()
        
        if os.path.exists(directory_path):
            try:
                os.startfile(directory_path)
            except Exception as ex:
                message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
                QMessageBox.critical(self, "An exception occurred", message)
        else:
            QMessageBox.warning(self, "Path Error", f"Path does not exist or is not a valid path:\n{directory_path}")

        
    def browse_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            self.input_folder.setText(folder)
            self.update_log_files_count(folder)
            
            
    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            self.output_folder.setText(folder)
    
    # Statusbar update function
    def update_log_files_count(self, folder):
        try:
            log_files = list(Path(folder).glob('*.log'))
            file_count = len(log_files)
            self.logfiles_count_statusbar.showMessage(f"Found {file_count} Log Files")
        except Exception as ex:
            message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
            self.logfiles_count_statusbar.setStyleSheet("color: #0d47a1")
            self.logfiles_count_statusbar.showMessage(f"Error counting Log files: {message}")
            
        
    def zip_log_files(self):
        input_folder = self.input_folder.text()
        output_folder = self.output_folder.text()
        compression_method = self.compression_method_combobox.currentText()
        delete_logfiles_after_zipping = self.delete_logfiles_checkbox.isChecked()
        patterns = [p.strip() for p in self.pattern_input.text().split(',') if p.strip()]
        date_filter_state = self.enable_date_filter_checkbox.isChecked()
        zip_files_older_than = self.zip_files_older_than.dateTime().toPython() # datetime object
        
        if not date_filter_state:
            if not input_folder or not output_folder and not patterns:
                QMessageBox.warning(self, "Error", "Please fill in all fields.")
                return
        
        if not os.path.exists(input_folder):
            QMessageBox.warning(self, "Input folder is empty", f"Input folder does not exist: {input_folder}")
            return
        
        if not os.path.exists(output_folder):
            reply = QMessageBox.question(self,"Output folder not found", f"The following output folder does not exist:\n{output_folder}\n\nDo you want to create it?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            # Check the user's response
            if reply == QMessageBox.Yes:
                try: 
                    os.makedirs(output_folder)
                    QMessageBox.information(self, "Success", f"Folder created: {output_folder}")
                except Exception as ex:
                    message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
                    QMessageBox.critical(self, "An exception occurred", f"Failed to create folder: {message}")
            else:
                return
        
        self.program_output.clear()
        
        # Set up worker and thread
        self.thread = QThread()
        self.worker = Worker(self, input_folder, output_folder, patterns, compression_method, delete_logfiles_after_zipping, date_filter_state, zip_files_older_than)
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.program_output.append)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.show_message.connect(self.show_message_box)  
        self.thread.started.connect(self.worker.run)
        
        # Start the thread
        self.thread.start()
        
        # Disable UI elements during processing
        self.set_ui_enabled(False)
        
    def set_ui_enabled(self, enabled):
        self.output_folder_button.setEnabled(enabled)
        self.output_folder.setEnabled(enabled)
        self.input_folder_button.setEnabled(enabled)
        self.input_folder.setEnabled(enabled)
        self.zip_button.setEnabled(enabled)
        self.compression_method_combobox.setEnabled(enabled)
        self.delete_logfiles_checkbox.setEnabled(enabled)
        self.zip_files_older_than.setEnabled(enabled)

    def on_worker_finished(self):
        self.set_ui_enabled(True)
        self.progress_bar.reset()
        self.thread.quit()
        self.thread.wait()
    
    def show_message_box(self, title, message):
        QMessageBox.information(self, title, message)  

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
