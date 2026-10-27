"""Application-owned validation lifetimes and cooperative Qt shutdown."""

from __future__ import annotations

import weakref

from PySide6.QtCore import QEvent, QObject, Qt, QThread, QTimer, Slot
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid


class _ValidationRun(QObject):
    """Relay queued results with explicit identity, independent of signal sender."""

    def __init__(self, supervisor, window, worker):
        super().__init__(supervisor)
        self.supervisor = supervisor
        self.window = weakref.ref(window)
        self.worker = worker
        self.binding = worker.binding
        self.thread = QThread(supervisor)
        self.retired = False

    def _publish(self, callback, *args):
        window = self.window()
        if (
            not self.retired
            and not self.supervisor.quit_pending
            and window is not None
            and isValid(window)
            and window._validation_worker is self.worker
            and window._validation_binding() == self.binding
        ):
            getattr(window, callback)(*args, _worker=self.worker)
        elif (
            callback in ("_on_validation_done", "_on_validation_error")
            and window is not None
            and isValid(window)
            and window._validation_worker is self.worker
        ):
            window._cleanup_validation_thread()

    @Slot(int, int, str)
    def progress(self, current, total, message):
        self._publish("_on_validation_progress", current, total, message)

    @Slot(object)
    def findings(self, findings):
        self._publish("_on_validation_findings_ready", findings)

    @Slot(object)
    def completed(self, report):
        self._publish("_on_validation_done", report)

    @Slot(str)
    def failed(self, message):
        self._publish("_on_validation_error", message)

    @Slot()
    def finished(self):
        window = self.window()
        if window is not None and isValid(window) and window._validation_worker is self.worker:
            window._cleanup_validation_thread()
        self.supervisor.release(self)


class ValidationSupervisor(QObject):
    """Keep the GUI event loop alive until every owned validation has finished.

    Cancellation is cooperative: a synchronous XPath must return before process
    shutdown can complete. Neither worker nor QThread belongs to the window.
    """

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.runs = {}
        self.quit_pending = False
        self._authorizing_quit = False
        self._quit_guard_installed = False
        self._original_quit_policy = False

    @property
    def shutdown_requested(self):
        return self.quit_pending or self._authorizing_quit

    def start(self, window, worker):
        if self.shutdown_requested:
            raise RuntimeError("Application shutdown is pending")
        if not self._quit_guard_installed:
            self._original_quit_policy = self.app.quitOnLastWindowClosed()
            self.app.setQuitOnLastWindowClosed(False)
            self.app.installEventFilter(self)
            self.app.lastWindowClosed.connect(self._last_window_closed)
            self._quit_guard_installed = True
        run = _ValidationRun(self, window, worker)
        self.runs[worker] = run
        worker.moveToThread(run.thread)
        run.thread.started.connect(worker.run)
        for signal, callback in (
            (worker.progress_changed, run.progress),
            (worker.findings_ready, run.findings),
            (worker.validation_completed, run.completed),
            (worker.validation_failed, run.failed),
        ):
            signal.connect(callback, Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(run.thread.quit, Qt.ConnectionType.DirectConnection)
        run.thread.finished.connect(worker.deleteLater)
        run.thread.finished.connect(run.finished, Qt.ConnectionType.QueuedConnection)
        return run.thread

    def retire(self, worker, *, cancel=False):
        run = self.runs.get(worker)
        if run is None:
            return
        run.retired = True
        if cancel:
            worker.cancel()

    def release(self, run):
        if self.runs.pop(run.worker, None) is None:
            return
        run.thread.deleteLater()
        run.deleteLater()
        if not self.runs and not self._authorizing_quit:
            self._restore_quit_guard()

    def _restore_quit_guard(self):
        if self._quit_guard_installed:
            self.app.removeEventFilter(self)
            self.app.lastWindowClosed.disconnect(self._last_window_closed)
            self.app.setQuitOnLastWindowClosed(self._original_quit_policy)
            self._quit_guard_installed = False
        if self.quit_pending:
            QTimer.singleShot(0, self._finish_quit)

    def _finish_quit(self):
        self.quit_pending = False
        self.app.quit()

    @Slot()
    def _last_window_closed(self):
        if self._original_quit_policy:
            self._request_quit()

    def _request_quit(self):
        if self.shutdown_requested:
            return
        windows = [
            window
            for window in self.app.topLevelWidgets()
            if window.isVisible() and callable(getattr(window, "_check_unsaved_changes", None))
        ]
        if any(getattr(window, "_close_authorizing", False) for window in windows):
            return
        self._authorizing_quit = True
        try:
            # closeEvent authorizes save/discard before retiring work. A veto
            # leaves the visible window and its validation completely intact.
            for window in windows:
                if not window.close():
                    return
            self.quit_pending = True
            for run in tuple(self.runs.values()):
                self.retire(run.worker, cancel=True)
        finally:
            self._authorizing_quit = False
            # A worker can finish inside the unsaved-changes modal event loop.
            if not self.runs:
                self._restore_quit_guard()

    def eventFilter(self, watched, event):  # noqa: N802
        if (
            watched is self.app
            and event.type() == QEvent.Type.Quit
            and (self.runs or self._authorizing_quit)
        ):
            self._request_quit()
            return True
        return False


def validation_supervisor():
    """Return the one application-owned validation lifetime supervisor."""
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("Validation requires a QApplication")
    supervisor = getattr(app, "_validation_supervisor", None)
    if supervisor is None:
        supervisor = ValidationSupervisor(app)
        app._validation_supervisor = supervisor
    return supervisor
