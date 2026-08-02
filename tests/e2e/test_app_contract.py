from eros.app.shell import MAIN_TABS, build_demo_state


def test_app_has_exactly_five_tabs() -> None:
    assert MAIN_TABS == (
        "Command Center",
        "Global Explorer",
        "Opportunity Engine",
        "Portfolio",
        "Research Lab",
    )


def test_demo_is_visibly_synthetic_and_execution_locked() -> None:
    state = build_demo_state()
    assert state.is_synthetic and "SYNTHETIC" in state.banner and not state.execution_enabled
