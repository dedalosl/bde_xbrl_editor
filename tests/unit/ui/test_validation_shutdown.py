"""Validation retirement must not block the GUI or outlive Qt safely."""

import os
import subprocess
import textwrap
import time
from threading import Event, Timer

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QMessageBox
from shiboken6 import isValid
from test_main_window_document_safety import document_window as _document_window_fixture
from test_validation_freshness import report

from bde_xbrl_editor.ui.validation_lifecycle import validation_supervisor
from bde_xbrl_editor.ui.widgets.validation_panel import ValidationWorker

document_window = _document_window_fixture


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.loader_settings_dialog._SETTINGS_FILE",
        tmp_path / "settings.json",
    )
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_saved_settings", lambda: {})
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_decimal_separator", lambda: ".")


@pytest.mark.parametrize("transition", ["document", "close"])
def test_retirement_keeps_gui_responsive(document_window, monkeypatch, qtbot, transition):
    window = document_window
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    original_policy = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(False)
    entered, release = Event(), Event()

    def validate(self, instance):
        entered.set()
        assert release.wait(3)
        return report()

    monkeypatch.setattr(
        "bde_xbrl_editor.validation.orchestrator.InstanceValidator.validate_sync", validate
    )
    monkeypatch.setattr(window, "_prompt_formula_general_variable_values", lambda: {})
    window._current_taxonomy = object()
    window._current_instance._dirty = False
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
    window.show()
    window._trigger_validation()
    thread = window._validation_thread
    heartbeat = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: heartbeat.append(time.monotonic()))
    fallback = Timer(0.6, release.set)
    fallback.start()
    try:
        qtbot.waitUntil(entered.is_set)
        timer.start()
        started = time.monotonic()
        if transition == "document":
            window._clear_browser_view_refs()
        else:
            assert window.close()
        assert time.monotonic() - started < 0.2
        qtbot.waitUntil(lambda: len(heartbeat) >= 3)
        assert not release.is_set()
        assert thread.isRunning()
        assert window._validation_thread is None
    finally:
        release.set()
        fallback.cancel()
        timer.stop()
        qtbot.waitUntil(lambda: not isValid(thread) or not thread.isRunning(), timeout=4000)
        qtbot.wait(30)
        app.setQuitOnLastWindowClosed(original_policy)


@pytest.mark.parametrize("operation", ["close", "quit"])
def test_application_drains_validation_before_exit(tmp_path, operation):
    script = textwrap.dedent("""
        import os, sys, time
        from pathlib import Path
        from threading import Event, Timer
        from PySide6.QtCore import QTimer, qInstallMessageHandler
        from PySide6.QtWidgets import QApplication
        import bde_xbrl_editor.ui.main_window as module
        import bde_xbrl_editor.ui.widgets.loader_settings_dialog as settings
        from bde_xbrl_editor.ui.widgets.validation_panel import ValidationWorker
        from bde_xbrl_editor.ui.validation_lifecycle import validation_supervisor
        from bde_xbrl_editor.validation.orchestrator import InstanceValidator
        module.load_loader_page_mode = lambda: "classic"
        settings._SETTINGS_FILE = Path(os.environ["XDG_CONFIG_HOME"]) / "settings.json"
        module.load_saved_settings = lambda: {}
        module.load_decimal_separator = lambda: "."
        app = QApplication([])
        window = module.MainWindow()
        window._check_unsaved_changes = lambda: True
        window._prompt_formula_general_variable_values = lambda: {}
        window._current_taxonomy = object()
        window._current_instance = object()
        entered, release, completed = Event(), Event(), Event()
        messages = []
        qInstallMessageHandler(lambda kind, context, message: messages.append(message))
        def validate(self, instance):
            entered.set()
            assert release.wait(4)
            completed.set()
            raise ValueError("retired worker exception")
        InstanceValidator.validate_sync = validate
        window.show()
        window._trigger_validation()
        beats = []
        heartbeat = QTimer()
        heartbeat.setInterval(10)
        heartbeat.timeout.connect(lambda: beats.append(time.monotonic()))
        heartbeat.start()
        def shutdown():
            if not entered.is_set():
                QTimer.singleShot(10, shutdown)
                return
            Timer(0.3, release.set).start()
            if sys.argv[1] == "close":
                assert window.close()
                window.deleteLater()
            else:
                app.quit()
                assert validation_supervisor().quit_pending
                old_worker = window._validation_worker
                window._trigger_validation()
                assert window._validation_worker is old_worker
        QTimer.singleShot(10, shutdown)
        QTimer.singleShot(5000, lambda: (release.set(), app.exit(99)))
        result = app.exec()
        assert result == 0, result
        assert completed.is_set(), "event loop exited before worker completed"
        assert len(beats) >= 10, len(beats)
        assert app.quitOnLastWindowClosed(), "application policy was not restored"
        assert not any("QThread: Destroyed" in message for message in messages), messages
        print("DRAINED", sys.argv[1], len(beats))
    """)
    env = dict(
        os.environ, QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=str(tmp_path), HOME=str(tmp_path)
    )
    result = subprocess.run(
        [os.sys.executable, "-c", script, operation],
        capture_output=True,
        text=True,
        env=env,
        timeout=12,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"DRAINED {operation}" in result.stdout
    print(result.stdout.strip())


@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.parametrize("quit_policy", [False, True])
def test_immediate_worker_finishes_and_deletes_once(
    document_window, monkeypatch, qtbot, failure, quit_policy
):
    window = document_window
    supervisor = validation_supervisor()
    app = supervisor.app
    original_policy = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(quit_policy)
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[-1]))
    monkeypatch.setattr(window, "_prompt_formula_general_variable_values", lambda: {})
    window._current_taxonomy = object()

    def validate(self, instance):
        if failure:
            raise ValueError("immediate failure")
        return report("immediate")

    monkeypatch.setattr(
        "bde_xbrl_editor.validation.orchestrator.InstanceValidator.validate_sync", validate
    )
    observations = []
    destroyed = []

    def create_worker(**kwargs):
        worker = ValidationWorker(**kwargs)
        observations.append(QSignalSpy(worker.finished))
        worker.destroyed.connect(lambda: destroyed.append("worker"))
        return worker

    # Observe before start: a zero-length run may finish before start() returns.
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.validation_panel.ValidationWorker", create_worker
    )
    window._trigger_validation()
    thread = window._validation_thread
    finished = observations[0]
    thread.destroyed.connect(lambda: destroyed.append("thread"))
    try:
        qtbot.waitUntil(lambda: not supervisor.runs)
        qtbot.waitUntil(lambda: not isValid(thread))
        assert finished.count() == 1
        assert sorted(destroyed) == ["thread", "worker"]
        assert window._validation_worker is None
        assert app.quitOnLastWindowClosed() is quit_policy
        window._cleanup_validation_thread(cancel=True)
        window._cleanup_validation_thread(cancel=True)
        if failure:
            assert errors == ["immediate failure"]
        else:
            assert window._validation_panel._current_report.findings[0].message == "immediate"
    finally:
        app.setQuitOnLastWindowClosed(original_policy)


def test_retired_callbacks_cannot_publish_or_cleanup_new_run(document_window, monkeypatch, qtbot):
    window = document_window
    entered = [Event(), Event()]
    release = [Event(), Event()]
    calls = []

    def validate(self, instance):
        index = len(calls)
        calls.append(instance)
        entered[index].set()
        assert release[index].wait(4)
        return report(f"run {index}")

    monkeypatch.setattr(
        "bde_xbrl_editor.validation.orchestrator.InstanceValidator.validate_sync", validate
    )
    monkeypatch.setattr(window, "_prompt_formula_general_variable_values", lambda: {})
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: pytest.fail("retired error"))
    window._current_taxonomy = object()
    window._trigger_validation()
    old = window._validation_worker
    try:
        qtbot.waitUntil(entered[0].is_set)
        # Already-queued signals survive disconnects and must retain run identity.
        old.progress_changed.emit(1, 1, "old queued progress")
        old.findings_ready.emit(report().findings)
        old.validation_completed.emit(report())
        old.validation_failed.emit("old queued error")
        window._clear_browser_view_refs()
        window._trigger_validation()
        new, new_thread = window._validation_worker, window._validation_thread
        qtbot.waitUntil(entered[1].is_set)
        assert window._validation_worker is new
        assert window._validation_panel._current_report is None
        assert window._validation_panel._model.rowCount() == 0
        release[0].set()
        qtbot.waitUntil(lambda: old not in validation_supervisor().runs)
        assert not isValid(old)
        assert window._validation_worker is new
        assert window._validation_thread is new_thread
        assert window._validation_panel._current_report is None
        release[1].set()
        qtbot.waitUntil(lambda: not validation_supervisor().runs)
        assert window._validation_panel._current_report.findings[0].message == "run 1"
    finally:
        for event in release:
            event.set()
        qtbot.waitUntil(lambda: not validation_supervisor().runs, timeout=5000)


def test_cancelled_unsaved_close_preserves_running_validation(document_window, monkeypatch, qtbot):
    window = document_window
    entered, release = Event(), Event()

    def validate(self, instance):
        entered.set()
        assert release.wait(3)
        return report()

    monkeypatch.setattr(
        "bde_xbrl_editor.validation.orchestrator.InstanceValidator.validate_sync", validate
    )
    monkeypatch.setattr(window, "_prompt_formula_general_variable_values", lambda: {})
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)
    window._current_taxonomy = object()
    window._current_instance._dirty = True
    window._trigger_validation()
    worker = window._validation_worker
    try:
        qtbot.waitUntil(entered.is_set)
        assert not window.close()
        assert window._validation_worker is worker
        assert not worker._cancel_event.is_set()
    finally:
        window._current_instance._dirty = False
        release.set()
        qtbot.waitUntil(lambda: not validation_supervisor().runs, timeout=4000)


def test_shutdown_during_prompt_cannot_start_another_run(document_window, monkeypatch, qtbot):
    window = document_window
    supervisor = validation_supervisor()
    entered, release = Event(), Event()

    def validate(self, instance):
        entered.set()
        assert release.wait(3)
        return report()

    monkeypatch.setattr(
        "bde_xbrl_editor.validation.orchestrator.InstanceValidator.validate_sync", validate
    )
    monkeypatch.setattr(window, "_prompt_formula_general_variable_values", lambda: {})
    window._current_taxonomy = object()
    window._trigger_validation()
    try:
        qtbot.waitUntil(entered.is_set)
        window._cleanup_validation_thread(cancel=True)

        def prompt():
            supervisor._request_quit()
            return {}

        monkeypatch.setattr(window, "_prompt_formula_general_variable_values", prompt)
        window._trigger_validation()
        assert window._validation_worker is None
        assert len(supervisor.runs) == 1
    finally:
        supervisor.quit_pending = False
        window._cleanup_validation_thread(cancel=True)
        release.set()
        qtbot.waitUntil(lambda: not supervisor.runs, timeout=4000)


@pytest.mark.parametrize(
    "answer", ["cancel", "save_cancel", "save_error", "accept", "cancel_finish"]
)
def test_application_quit_authorizes_before_retirement(tmp_path, answer):
    script = textwrap.dedent("""
        import os, sys
        from datetime import datetime
        from pathlib import Path
        from threading import Event
        from types import SimpleNamespace
        from PySide6.QtCore import QEventLoop, QTimer, qInstallMessageHandler
        from PySide6.QtWidgets import QApplication, QMessageBox
        import bde_xbrl_editor.ui.main_window as module
        import bde_xbrl_editor.ui.widgets.loader_settings_dialog as settings
        from bde_xbrl_editor.ui.validation_lifecycle import validation_supervisor
        from bde_xbrl_editor.validation.models import ValidationReport
        from bde_xbrl_editor.validation.orchestrator import InstanceValidator
        settings._SETTINGS_FILE = Path(os.environ["XDG_CONFIG_HOME"]) / "settings.json"
        module.load_loader_page_mode = lambda: "classic"
        module.load_saved_settings = lambda: {}
        module.load_decimal_separator = lambda: "."
        app = QApplication([])
        window = module.MainWindow()
        window._prompt_formula_general_variable_values = lambda: {}
        window._current_taxonomy = object()
        window._current_instance = SimpleNamespace(has_unsaved_changes=True)
        entered, release = Event(), Event()
        messages, errors, guards, beats = [], [], [], []
        qInstallMessageHandler(lambda kind, context, message: messages.append(message))
        expected = ValidationReport("instance.xbrl", "Test", "1", datetime(2025,1,1), (), True)
        def validate(self, instance):
            entered.set()
            assert release.wait(4)
            return expected
        InstanceValidator.validate_sync = validate
        original_guard = window._check_unsaved_changes
        def guard():
            guards.append(not release.is_set())
            return original_guard()
        window._check_unsaved_changes = guard
        answer = sys.argv[1]
        def question(*args):
            if answer == "cancel_finish":
                loop = QEventLoop()
                QTimer.singleShot(10, release.set)
                QTimer.singleShot(50, app.quit)
                QTimer.singleShot(80, loop.quit)
                loop.exec()
            else:
                # Recursive quit from a modal dialog must not repeat its guard.
                app.quit()
            return (
                QMessageBox.StandardButton.Cancel
                if answer.startswith("cancel") else QMessageBox.StandardButton.Save
            )
        QMessageBox.question = question
        window._on_save = lambda: {
            "save_cancel": module.SaveResult.CANCELLED,
            "save_error": module.SaveResult.ERROR,
            "accept": module.SaveResult.SUCCESS,
        }[answer]
        window.show()
        window._trigger_validation()
        worker = window._validation_worker
        supervisor = validation_supervisor()
        heartbeat = QTimer()
        heartbeat.setInterval(10)
        heartbeat.timeout.connect(lambda: beats.append(1))
        heartbeat.start()
        def fail(exc):
            errors.append(str(exc))
            release.set()
            app.exit(91)
        def check_result():
            if supervisor.runs:
                QTimer.singleShot(10, check_result)
                return
            try:
                assert window.isVisible(), "vetoed quit closed the window"
                assert window._validation_panel._current_report == expected, "veto lost report"
                assert guards == [True], guards
                window._check_unsaved_changes = lambda: True
                window.close()
                app.quit()
            except Exception as exc:
                fail(exc)
        def probe():
            try:
                assert guards == [True], "unsaved guard was not consulted before worker release"
                if answer == "accept":
                    assert not window.isVisible()
                    assert supervisor.quit_pending
                    assert worker._cancel_event.is_set()
                else:
                    assert window.isVisible()
                    assert not supervisor.quit_pending
                    assert not worker._cancel_event.is_set(), "vetoed quit cancelled worker"
                    if worker in supervisor.runs:
                        assert not supervisor.runs[worker].retired, "vetoed quit retired worker"
                release.set()
                if answer != "accept":
                    check_result()
            except Exception as exc:
                fail(exc)
        def shutdown():
            if not entered.is_set():
                QTimer.singleShot(10, shutdown)
                return
            app.quit()
            QTimer.singleShot(100, probe)
        QTimer.singleShot(10, shutdown)
        QTimer.singleShot(5000, lambda: fail("shutdown timeout"))
        result = app.exec()
        assert result == 0, (result, errors)
        assert guards == [True], guards
        assert len(beats) >= 3, len(beats)
        assert not supervisor.runs
        assert app.quitOnLastWindowClosed()
        assert not any("QThread: Destroyed" in message for message in messages), messages
        print("AUTHORIZED", answer, "GUARDS", len(guards), "HEARTBEATS", len(beats))
    """)
    env = dict(
        os.environ, QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=str(tmp_path), HOME=str(tmp_path)
    )
    result = subprocess.run(
        [os.sys.executable, "-c", script, answer],
        capture_output=True,
        text=True,
        env=env,
        timeout=12,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout.strip())
