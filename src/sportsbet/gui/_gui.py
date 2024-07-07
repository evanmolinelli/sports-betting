"""GUI for sports-betting."""

from nicegui import ui

from sportsbet.gui._data import (
    create_control_ui,
    create_data_ui,
    create_extraction_ui,
    create_filter_ui,
    create_sport_ui,
    set_buttons_visibility,
)
from sportsbet.gui._state import state


def select_mode() -> None:
    """Select the mode."""
    if state['mode_ui'].value == 'Data' and 'sport_ui' not in state:
        create_sport_ui.refresh()
        create_control_ui.refresh()
        create_cancel_ui.refresh()
        set_buttons_visibility(0)


def select_cancel() -> None:
    """Select the cancel button."""
    for key in state.copy():
        if key != 'mode_ui':
            state.pop(key)
    create_mode_ui.refresh()
    create_sport_ui.refresh()
    create_filter_ui.refresh()
    create_extraction_ui.refresh()
    create_data_ui.refresh()
    create_control_ui.refresh()
    create_cancel_ui.refresh()


@ui.refreshable
def create_mode_ui() -> None:
    """Create mode UI elements."""
    with ui.row():
        state['mode_ui'] = ui.toggle(['Data', 'Betting'], on_change=select_mode)
    with ui.row():
        ui.label('Select either to download data or evaluate betting strategies').tailwind.font_size('xs')


@ui.refreshable
def create_cancel_ui() -> None:
    """Create cancel UI element."""
    if state['mode_ui'].value in ('Data', 'Betting'):
        state['cancel_ui'] = ui.button(icon='cancel', on_click=select_cancel)


def main() -> None:
    """Run the UI of the application."""

    # Header
    with ui.header(bordered=True).classes('bg-sky-400'), ui.element('q-toolbar'):  # noqa: SIM117
        with ui.element('q-toolbar-title').props('align=center'):
            ui.markdown('Sports-Betting').style('color: black').tailwind.font_size('6xl').font_weight('semibold')
            ui.markdown('Data extraction and model evaluation toolbox').tailwind.font_size('lg').font_weight('light')

    # Left drawer
    with ui.left_drawer(bordered=True, elevated=True) as left_drawer:
        left_drawer.props('width=450')
        create_mode_ui()
        create_sport_ui()
        create_filter_ui()
        create_extraction_ui()
        ui.separator()
        with ui.row():
            create_control_ui()
            create_cancel_ui()

    # Main
    create_data_ui()

    ui.run(reload=False)
