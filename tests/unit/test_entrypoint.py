"""Tests for application entrypoint behavior."""

from __future__ import annotations


def test_main_prepares_multiprocessing_before_qapplication(monkeypatch) -> None:
    from bde_xbrl_editor import __main__ as entrypoint

    calls: list[str] = []

    def fake_freeze_support() -> None:
        calls.append("freeze_support")

    class FakeApplication:
        def exec(self) -> int:
            calls.append("exec")
            return 0

    class FakeWindow:
        def show(self) -> None:
            calls.append("show")

    monkeypatch.setattr(entrypoint.multiprocessing, "freeze_support", fake_freeze_support)
    monkeypatch.setattr(
        entrypoint,
        "_create_qapplication",
        lambda _argv: calls.append("qapplication") or FakeApplication(),
    )
    monkeypatch.setattr(entrypoint, "_create_main_window", lambda: FakeWindow())

    with monkeypatch.context() as ctx:
        ctx.setattr(entrypoint.sys, "argv", ["bde-xbrl-editor"])
        ctx.setattr(entrypoint.sys, "exit", lambda code=0: calls.append(f"exit:{code}"))
        entrypoint.main()

    assert calls == ["freeze_support", "qapplication", "show", "exec", "exit:0"]
