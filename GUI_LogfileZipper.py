from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QGroupBox, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QRadioButton, 
                             QListWidget, QTextEdit, QProgressBar, QStatusBar,
                             QCheckBox,QMenu,QFileDialog, QMessageBox, QFrame, 
                             QSpacerItem, QSizePolicy, QTableView, QHeaderView, QInputDialog, QDialog, QTreeView, QFileSystemModel)
from PySide6.QtGui import QIcon, QAction, QStandardItemModel, QStandardItem, QCloseEvent, QTextCursor, QIcon
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSortFilterProxyModel, QObject, QTimer, QDir
from pathlib import Path
import re
import py7zr
import os
import sys

class Worker(QObject):
    progress_updated = Signal(int)
    log_message = Signal(str)
    finished = Signal()

    def __init__(self, input_folder, output_folder, patterns):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.patterns = patterns

    def run(self):
        try:
            for pattern in self.patterns:
                regex = f"^{re.escape(pattern).replace('\\*', '.*')}$"
                matching_files = [f for f in os.listdir(self.input_folder) if re.match(regex, f)]
                total_files = len(matching_files)
                if matching_files:
                    zip_filename = f"{pattern.replace('*', '')}.7z"
                    zip_path = os.path.join(self.output_folder, zip_filename)
                    
                    with py7zr.SevenZipFile(zip_path, "w") as zipf:
                        for index, file in enumerate(matching_files):
                            file_path = os.path.join(self.input_folder, file)
                            zipf.write(file_path, file)
                            self.log_message.emit(f"Processing file {file}")
                            progress = int((index + 1) / total_files * 100)
                            self.progress_updated.emit(progress)

                    self.log_message.emit(f"Created Archive: {zip_filename} with {len(matching_files)} files\nDeleted {len(matching_files)} log files that were zipped.")
                else:
                    self.log_message.emit(f"No files found matching: {pattern}")
            
            self.finished.emit()
        except Exception as e:
            self.log_message.emit(f"An error occurred: {str(e)}")
            self.finished.emit()

class RegexGeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Regex Generator and Tester")
        self.setWindowIcon(QIcon("_internal\icon\logo.ico"))
        self.setGeometry(100, 100, 600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Input for log file patterns
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Enter log file patterns (comma-separated)")
        layout.addWidget(QLabel("Log File Patterns (separate multiple entries using commas):"))
        layout.addWidget(self.pattern_input)

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
        patterns = [p.strip() for p in self.pattern_input.text().split(',') if p.strip()]
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
        self.setWindowTitle("Log File Zipper")
        self.setWindowIcon(QIcon("_internal\icon\logo.ico"))
        self.setGeometry(500, 250, 1000, 700)
        self.saveGeometry()
        self.initUI()
        
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
        input_folder_button = QPushButton("Browse")
        input_folder_button.clicked.connect(self.browse_input_folder)
        input_folder_layout.addWidget(input_folder_button)
        layout.addWidget(QLabel("Input Folder:"))
        layout.addLayout(input_folder_layout)

        # Output folder selection
        self.output_folder = QLineEdit()
        self.output_folder.setPlaceholderText("Choose a folder where to save the zipped archives...")
        output_folder_layout = QHBoxLayout()
        output_folder_layout.addWidget(self.output_folder)
        output_folder_button = QPushButton("Browse")
        output_folder_button.clicked.connect(self.browse_output_folder)
        output_folder_layout.addWidget(output_folder_button)
        layout.addWidget(QLabel("Output Folder:"))
        layout.addLayout(output_folder_layout)
        
        
        # Input for log file patterns
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Enter log file patterns (comma-separated)")
        layout.addWidget(QLabel("Log File Patterns (comma-separated):"))
        layout.addWidget(self.pattern_input)
        
        buttons_layout = QHBoxLayout()

        # Zip button
        zip_button = QPushButton("Start Zipping Log Files")
        zip_button.clicked.connect(self.zip_log_files)
        buttons_layout.addWidget(zip_button)

        # Open Regex Generator button
        regex_button = QPushButton("Open Regex Generator")
        regex_button.clicked.connect(self.open_regex_generator)
        buttons_layout.addWidget(regex_button)
        
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
        self.file_system_model.setRootPath(QDir.rootPath())  # Set root path to the filesystem's root
        self.file_system_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)  # Show all dirs and files

        # Set the model to the tree view
        self.tree_view.setModel(self.file_system_model)
        self.tree_view.setRootIndex(self.file_system_model.index(QDir.homePath()))  # Set root index to the user's home directory

        # Optional: Customize the view
        self.tree_view.setColumnWidth(0, 250)  # Adjust column width
        self.tree_view.setHeaderHidden(False)   # Show the header
        self.tree_view.setSortingEnabled(True)  # Enable sorting
        
    
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
        patterns = [p.strip() for p in self.pattern_input.text().split(',') if p.strip()]
        
        if not input_folder or not output_folder or not patterns:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return
        
        if not os.path.exists(input_folder):
            QMessageBox.critical(self, "Error", f"Input folder does not exist: {input_folder}")
            return
        
        if not os.path.exists(output_folder):
            QMessageBox.critical(self, "Error", f"Output folder does not exist: {output_folder}")
            return
        
        self.program_output.clear()
        
        # Set up worker and thread
        self.thread = QThread()
        self.worker = Worker(input_folder, output_folder, patterns)
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.log_message.connect(self.program_output.append)
        self.worker.finished.connect(self.on_worker_finished)
        self.thread.started.connect(self.worker.run)
        
        # Start the thread
        self.thread.start()

    def on_worker_finished(self):
        QMessageBox.information(self, "Success", "Zipping process completed.")
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
        }
        QLabel {
            color: #ffffff;
        }
        QLineEdit, QTextEdit, QTreeView {
            background-color: #3a3a3a;
            border: 1px solid #555555;
            padding: 2px;
            color: #ffffff;
        }
        QPushButton {
            background-color: #0d47a1;
            color: white;
            border: none;
            padding: 5px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #1565c0;
        }
        QPushButton:pressed {
            background-color: #0a3d91;
        }
        QTreeView::item:selected {
            background-color: #1565c0;
        }
        QMenuBar {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #3a3a3a;
        }
        QMenu {
            background-color: #2b2b2b;
            color: #ffffff;
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
            border-radius: 5px;
            text-align: center;
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
