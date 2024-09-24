from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QTextEdit, QProgressBar, QStatusBar, QCheckBox,
                             QFileDialog, QMessageBox, QSizePolicy, QDialog, QTreeView, QFileSystemModel)
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QDropEvent
from PySide6.QtCore import QThread, Signal, QObject, QDir
from pathlib import Path
import re
import zipfile
import os
import sys

class Worker(QObject):
    progress_updated = Signal(int)
    log_message = Signal(str)
    finished = Signal()

    def __init__(self, input_folder, output_folder, patterns, compression_method, delete_logfiles_after_zipping):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.patterns = patterns
        self.compression_method_text = compression_method  
        self.delete_logfiles_checkbox = delete_logfiles_after_zipping
        
        if compression_method  == "zlib (Fast)":
            self.compression_method = zipfile.ZIP_DEFLATED
        elif compression_method  == "bz2 (Good)":
            self.compression_method = zipfile.ZIP_BZIP2
        elif compression_method  == "lzma (Highest)":
            self.compression_method = zipfile.ZIP_LZMA

    def run(self):
        try:
            counter = 0 # Counter to display compressing archive 1 out of n
            self.log_message.emit(f"Starting to compress log files with compression method: {self.compression_method_text}")
            for pattern in self.patterns:
                counter += 1 # Updating the counter
                regex = f"^{re.escape(pattern).replace('\\*', '.*')}$"
                matching_files = [f for f in os.listdir(self.input_folder) if re.match(regex, f)]
                total_files = len(matching_files)
                if matching_files:
                    # Print processing message
                    creating_archive_message = f"Creating archive {pattern.replace('*', '')}.zip ({counter}/{len(self.patterns)})"
                    self.log_message.emit(len(creating_archive_message) * "-")
                    self.log_message.emit(creating_archive_message)
                    self.log_message.emit(len(creating_archive_message) * "-")
                    # Continue processing
                    zip_filename = f"{pattern.replace('*', '')}.zip"
                    zip_path = os.path.join(self.output_folder, zip_filename)
                    self.log_message.emit("Starting zipping of log files...")
                    with zipfile.ZipFile(zip_path, "w", compression=self.compression_method) as zipf:
                        for index, file in enumerate(matching_files):
                            file_path = os.path.join(self.input_folder, file)
                            zipf.write(file_path, arcname=file)
                            if self.delete_logfiles_checkbox:
                                os.unlink(file_path) # Deletes zipped log files
                            self.log_message.emit(f"Zipping file {file}")
                            progress = int((index + 1) / total_files * 100)
                            self.progress_updated.emit(progress)
                                
                    if self.delete_logfiles_checkbox:
                        task_complete_message = f"Task completed - Created archive '{zip_filename}' with {len(matching_files)} files.\nCleaning up - Deleted {len(matching_files)} log files that were zipped."
                        self.log_message.emit(task_complete_message)
                    else:
                        task_complete_message = f"Task completed - Created archive '{zip_filename}' with {len(matching_files)} files."
                        self.log_message.emit(task_complete_message)
                    
                else:
                    self.log_message.emit(f"No files found matching pattern(s): {pattern}")
            
            self.finished.emit()
        except Exception as e:
            self.log_message.emit(f"An error occurred: {str(e)}")
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

class RegexGeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Regex Generator and Tester")
        self.setWindowIcon(QIcon("_internal\\icon\\zipzap.ico"))
        self.setGeometry(100, 100, 600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Input for log file patterns
        self.patter_input_generator = QLineEdit()
        self.patter_input_generator.setPlaceholderText("Enter log file patterns (comma-separated)")
        layout.addWidget(QLabel("Log File Patterns (separate multiple entries using commas):"))
        layout.addWidget(self.patter_input_generator)

        # Generate Regex button
        self.generate_button = QPushButton("Generate Regex")
        self.generate_button.clicked.connect(self.generate_regex)
        layout.addWidget(self.generate_button)

        # Display generated regex
        self.regex_display = QLineEdit()
        self.regex_display.setReadOnly(True)
        layout.addWidget(QLabel("Generated Regex:"))
        layout.addWidget(self.regex_display)

        # Test input
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("Enter a test string")
        layout.addWidget(QLabel("Test String:"))
        layout.addWidget(self.test_input)

        # Test button
        self.test_button = QPushButton("Test Regex")
        self.test_button.clicked.connect(self.test_regex)
        layout.addWidget(self.test_button)

        # Results display
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        layout.addWidget(QLabel("Test Results:"))
        layout.addWidget(self.results_display)

        self.setLayout(layout)

    def generate_regex(self):
        patterns = [p.strip() for p in self.patter_input_generator.text().split(',') if p.strip()]
        if not patterns:
            self.regex_display.setText("")
            return

        regex_parts = []
        for pattern in patterns:
            escaped_pattern = re.escape(pattern).replace(r'\*', '.*')
            regex_parts.append(f"({escaped_pattern})")

        full_regex = '^' + '|'.join(regex_parts) + '$'
        self.regex_display.setText(full_regex)

    def test_regex(self):
        regex = self.regex_display.text()
        test_string = self.test_input.text()

        if not regex or not test_string:
            self.results_display.setText("Please generate a regex and enter a test string.")
            return

        try:
            match = re.match(regex, test_string)
            if match:
                self.results_display.setText(f"Match found: {match.group()}")
            else:
                self.results_display.setText("No match found.")
        except re.error as e:
            self.results_display.setText(f"Regex error: {str(e)}")

class MainWindow(QMainWindow):
    progress_updated = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Logfile Zipper v1.0.2")
        self.setWindowIcon(QIcon("_internal\\icon\\zipzap.ico"))
        self.setGeometry(500, 250, 1000, 700)
        self.saveGeometry()
        self.initUI()
        
        # Create the menu bar
        self.create_menu_bar()
        
        # Apply the custom dark theme
        self.apply_custom_dark_theme()
        
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
        self.pattern_input.setPlaceholderText("Enter log file patterns (comma-separated)")
        self.pattern_input.setClearButtonEnabled(True)
        layout.addWidget(QLabel("Log File Patterns (comma-separated):"))
        layout.addWidget(self.pattern_input)
        
        buttons_layout = QHBoxLayout()
        
        # Compression CombBox
        self.compression_method_combobox = QComboBox()
        compression_method_combobox_label = QLabel("Compression method:")
        self.compression_method_combobox.addItems(["zlib (Fast)", "bz2 (Good)", "lzma (Highest)"])
        
        self.delete_logfiles_checkbox = QCheckBox("Delete log files after zipping?")

        buttons_layout.addWidget(compression_method_combobox_label)
        buttons_layout.addWidget(self.compression_method_combobox)
        buttons_layout.addWidget(self.delete_logfiles_checkbox)
        
        # Zip button
        self.zip_button = QPushButton("Start Zipping Log Files")
        self.zip_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.zip_button.clicked.connect(self.zip_log_files)
        buttons_layout.addWidget(self.zip_button)

        # Open Regex Generator button
        self.regex_button = QPushButton("Open Regex Generator")
        self.regex_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.regex_button.clicked.connect(self.open_regex_generator)
        buttons_layout.addWidget(self.regex_button)
        
        layout.addLayout(buttons_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # Statusbar
        self.logfiles_count_statusbar = QStatusBar()
        self.setStatusBar(self.logfiles_count_statusbar)
        self.logfiles_count_statusbar.setSizeGripEnabled(False)
        self.logfiles_count_statusbar.setStyleSheet("font-size: 16px; font-weight: bold; color: #0c6cd4")
        statusbar_layout = QHBoxLayout()
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
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            
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
        open_input_action = QAction("Open log files folder", self)
        open_input_action.setStatusTip("Opens the log files input folder")
        open_input_action.triggered.connect(self.open_input_folder)
        open_menu.addAction(open_input_action)
        open_output_action = QAction("Open zipped archives folder ", self)
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
            Fast compression and decompression.
            Provides a good balance between compression speed and compression ratio.
        Cons:
            The compression ratio is generally lower than bz2 and lzma.
            
        Best for: General use cases where compatibility, speed, and reasonable compression are needed (e.g., web transfers, archives)."""
        
            self.program_output.setText(f"Selected compression method: {combobox_text} - Description:\n{desc_txt}")
        
        elif combobox_text == "bz2 (Good)":
            desc_txt = """
        Pros:
            Higher compression ratio than zlib for most files.
            Good decompression speed.
        Cons:
            Slower compression speed compared to zlib.
            
        Best for: Situations where higher compression is desired and compression speed is less of a concern (e.g., backups, log files)."""

            self.program_output.setText(f"Selected compression method: {combobox_text} - Description:\n{desc_txt}")
        
        elif  combobox_text == "lzma (Highest)":
            desc_txt = """
        Pros:
            Achieves the highest compression ratio among the three methods.
            Good choice for very large files or when maximum compression is necessary.
        Cons:
            Slower compression and decompression speed.
            Consumes more memory during compression.
            
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
                QMessageBox.critical(self, "Error", message)
        else:
            QMessageBox.warning(self, "Error", f"Path does not exist or is not a valid path:\n{directory_path}")
    
    
    # Open Zipped Archive output folder
    def open_output_folder(self):
        directory_path = self.output_folder.text()
        
        if os.path.exists(directory_path):
            try:
                os.startfile(directory_path)
            except Exception as ex:
                message = f"An exception of type {type(ex).__name__} occurred. Arguments: {ex.args!r}"
                QMessageBox.critical(self, "Error", message)
        else:
            QMessageBox.warning(self, "Error", f"Path does not exist or is not a valid path:\n{directory_path}")

        
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
            
            
    def open_regex_generator(self):
        dialog = RegexGeneratorDialog(self)
        dialog.exec()
        
        
    def zip_log_files(self):
        input_folder = self.input_folder.text()
        output_folder = self.output_folder.text()
        compression_method = self.compression_method_combobox.currentText()
        delete_logfiles_after_zipping = self.delete_logfiles_checkbox.isChecked()
        patterns = [p.strip() for p in self.pattern_input.text().split(',') if p.strip()]
        
        if not input_folder or not output_folder or not patterns:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return
        
        if not os.path.exists(input_folder):
            QMessageBox.critical(self, "Error", f"Input folder does not exist: {input_folder}")
            return
        
        if not os.path.exists(output_folder):
            reply = QMessageBox.warning(self,"Warning", f"Output folder does not exist: {output_folder}\nDo you want to create it?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            # Check the user's response
            if reply == QMessageBox.Yes:
                try:
                    os.makedirs(output_folder)
                    QMessageBox.information(self, "Success", f"Folder created: {output_folder}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create folder: {e}")
            else:
                return
        
        self.program_output.clear()
        
        # Set up worker and thread
        self.thread = QThread()
        self.worker = Worker(input_folder, output_folder, patterns, compression_method, delete_logfiles_after_zipping)
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.program_output.append)
        self.worker.finished.connect(self.on_worker_finished)
        self.thread.started.connect(self.worker.run)
        
        # Start the thread
        self.thread.start()
        
        # Disabled button on run
        self.output_folder_button.setDisabled(True)
        self.output_folder.setDisabled(True)
        self.input_folder_button.setDisabled(True)
        self.input_folder.setDisabled(True)
        self.zip_button.setDisabled(True)
        self.regex_button.setDisabled(True)
        self.compression_method_combobox.setDisabled(True)
        self.delete_logfiles_checkbox.setDisabled(True)

    def on_worker_finished(self):
        QMessageBox.information(self, "Success", "Zipping process completed.")
        self.output_folder_button.setDisabled(False)
        self.output_folder.setDisabled(False)
        self.input_folder_button.setDisabled(False)
        self.input_folder.setDisabled(False)
        self.zip_button.setDisabled(False)
        self.regex_button.setDisabled(False)
        self.compression_method_combobox.setDisabled(False)
        self.delete_logfiles_checkbox.setDisabled(False)
        self.progress_bar.reset()
        self.thread.quit()
        self.thread.wait()
            
    def apply_custom_dark_theme(self):
        self.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
        }
        QLabel {
            color: #ffffff;
            font: bold;
        }
        QLineEdit, QTextEdit, QTreeView {
            background-color: #3a3a3a;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
        }
        QLineEdit:focus, QTextEdit:focus, QTreeView:focus {
            border-color: #0d47a1;
            background-color: #3a3a3a;
        }
        QPushButton {
            background-color: #0d47a1;
            color: white;
            border-radius: 6px;
            padding: 8px 12px;
            font-weight: 500;
            min-width: 90px;
        }
        QPushButton:hover {
            background-color: #1565c0;
        }
        QPushButton:pressed {
            background-color: #0a3d91;
        }
        QPushButton:disabled {
            background-color: #808080;
        }
        QTreeView::item:selected {
            background-color: #1565c0;
        }
        QMenuBar {
            border-bottom: 2px solid #0d47a1;
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #3a3a3a;
        }
        QMenu {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #424242;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background-color: #1565c0;
        }
        QStatusBar {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QProgressBar {
            border: 2px solid grey;
            border-radius: 6px;
            text-align: center;
            font-weight: 600;
            font: bold 
        }
        QProgressBar::chunk {
            background-color: #0d47a1;
            width: 10px;
            margin: 0.5px
        }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
