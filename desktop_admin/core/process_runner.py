"""
Asynchronous Process Runner using QProcess for Desktop Admin Suite.
Captures real-time output streams with process lifecycle signals.
"""

import os
import sys
from PyQt5.QtCore import QObject, QProcess, pyqtSignal

class ProcessRunner(QObject):
    output_received = pyqtSignal(str)
    started = pyqtSignal()
    finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.started.connect(self.started.emit)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_error)
        self.is_running = False

    def start_command(self, program: str, args: list, cwd: str = None):
        """Start a process with program and arguments."""
        if self.is_running:
            self.stop()

        if cwd:
            self.process.setWorkingDirectory(cwd)

        # Ensure UTF-8 decoding
        env = self.process.processEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(env)

        self.is_running = True
        self.process.start(program, args)

    def start_python_script(self, script_path: str, args: list = None, cwd: str = None):
        """Convenience method to run a python script."""
        py_exe = sys.executable
        all_args = [script_path] + (args or [])
        self.start_command(py_exe, all_args, cwd)

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _handle_finished(self, exit_code, exit_status):
        self.is_running = False
        self.finished.emit(exit_code)

    def _handle_error(self, error):
        self.is_running = False
        msg = f"Process Error: {error}"
        self.error_occurred.emit(msg)

    def stop(self):
        """Terminate the running process safely."""
        if self.is_running:
            self.process.terminate()
            if not self.process.waitForFinished(1500):
                self.process.kill()
            self.is_running = False
