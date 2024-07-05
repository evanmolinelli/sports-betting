"""GUI for sports-betting."""

import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd
from nicegui import run, ui
from sportsbet import Param
from sportsbet.datasets import SoccerDataLoader
from sportsbet.datasets._base import _BaseDataLoader

DATALOADERS = {
    'Soccer': SoccerDataLoader,
    'NBA': _BaseDataLoader,
    'NFL': _BaseDataLoader,
    'NHL': _BaseDataLoader,
}

state: dict[str, Any] = {}


def create_control_ui() -> None:  # noqa: C901, PLR0915
    """Create control UI elements."""

    # Sport
    def get_params() -> list[Param]:
        """Get dataloader's available parameters."""
        return DATALOADERS[state['sport_ui'].value].get_all_params()

    async def select_sport() -> None:
        """Select the dataloader."""
        dataloader_name = state['sport_ui'].value
        if dataloader_name == 'Soccer':
            spinner = ui.spinner(size='lg')
            state['all_params'] = await run.io_bound(get_params)
            spinner.set_visibility(False)
            create_filter_ui.refresh()
            state['arrow_sport_ui'].set_visibility(False)
            state['arrow_filter_ui'].set_visibility(True)
            state['sport_ui'].set_enabled(False)
        elif dataloader_name != 'Soccer' and dataloader_name is not None:
            ui.notify('Soccer is the only currently available sport.')
        else:
            ui.notify('Please select a sport to proceed.')

    # Filter
    def get_odds_types() -> list[str]:
        """Get dataloader's available odds types."""
        return state['dataloader'].get_odds_types()

    async def select_filter() -> None:
        """Select the filter to create dataloader."""
        if state['filter_ui'].selected:
            param_grid = [
                {name: [val] for name, val in param.items() if name != 'id'} for param in state['filter_ui'].selected
            ]
            state['dataloader'] = DATALOADERS[state['sport_ui'].value](param_grid=param_grid)  # type: ignore  # noqa: PGH003
            spinner = ui.spinner(size='lg')
            state['odds_types'] = await run.io_bound(get_odds_types)
            spinner.set_visibility(False)
            create_extraction_ui.refresh()
            state['arrow_filter_ui'].set_visibility(False)
            state['arrow_extraction_ui'].set_visibility(True)
            state['filter_ui'].props('disabled')
        else:
            ui.notify('Please select at least one row of filter table.')

    # Extraction
    def get_train_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
        """Get the training data."""
        return state['dataloader'].extract_train_data(
            odds_type=state['odds_type_ui'].value,
            drop_na_thres=state['drop_na_thres_ui'].value,
        )

    def get_fixtures_data() -> tuple[pd.DataFrame, None, pd.DataFrame | None]:
        """Get the fixtures data."""
        return state['dataloader'].extract_fixtures_data()

    async def select_extraction() -> None:
        """Select the extraction parameters of training data."""
        spinner = ui.spinner(size='lg')
        state['X_train'], state['Y_train'], state['O_train'] = await run.io_bound(get_train_data)
        state['X_fix'], state['Y_fix'], state['O_fix'] = await run.io_bound(get_fixtures_data)
        spinner.set_visibility(False)
        create_data_ui.refresh()
        state['arrow_extraction_ui'].set_visibility(False)
        state['odds_type_ui'].props('disabled')
        state['drop_na_thres_ui'].set_enabled(False)
        state['download_ui'].set_visibility(True)

    def download_data() -> None:
        """Dowload the dataloader."""
        with TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / 'dataloader.pkl'
            state['dataloader'].save(dest_path)
            with Path.open(Path(dest_path), 'rb') as dataloader_file:
                ui.download(dataloader_file.read(), 'dataloader.pkl')

    def refresh_ui() -> None:
        """Refresh the UI."""
        for key in state.copy():
            if not key.startswith(('arrow', 'download')) and key not in 'sport_ui':
                state.pop(key)
            else:
                state['arrow_sport_ui'].set_visibility(True)
                state['arrow_filter_ui'].set_visibility(False)
                state['arrow_extraction_ui'].set_visibility(False)
                state['download_ui'].set_visibility(False)
                state['sport_ui'].set_enabled(True)
                state['sport_ui'].set_value(None)
        create_filter_ui.refresh()
        create_filter_ui.refresh()
        create_extraction_ui.refresh()
        create_data_ui.refresh()

    # Buttons
    with ui.row():
        state['arrow_sport_ui'] = ui.button(icon='play_arrow', on_click=select_sport)
        state['arrow_filter_ui'] = ui.button(icon='play_arrow', on_click=select_filter)
        state['arrow_extraction_ui'] = ui.button(icon='play_arrow', on_click=select_extraction)
        state['download_ui'] = ui.button(icon='download', on_click=download_data)
        state['arrow_filter_ui'].set_visibility(False)
        state['arrow_extraction_ui'].set_visibility(False)
        state['download_ui'].set_visibility(False)
        ui.button(icon='cancel', on_click=refresh_ui)


def create_sport_ui() -> None:
    """Create the sport UI elements."""
    with ui.row():
        ui.label('Sport').style('color: rgb(56 189 248)').tailwind.font_size('xl')
    with ui.row():
        ui.label('Select one of the available sports').tailwind.font_size('xs')
    with ui.row():
        state['sport_ui'] = ui.radio(list(DATALOADERS)).props('inline')


@ui.refreshable
def create_filter_ui() -> None:
    """Create the filter UI elements."""
    if 'all_params' in state:
        all_params = state['all_params']
        params_names = next(tuple(param.keys()) for param in all_params)
        columns = [
            {
                'name': 'id',
                'label': 'ID',
                'field': 'id',
                'required': True,
                'classes': 'hidden',
                'headerClasses': 'hidden',
            },
        ]
        columns += [
            {'name': name, 'label': name.title(), 'field': name, 'required': False, 'sortable': True}
            for name in params_names
        ]
        rows = [{**param, 'id': num + 1} for num, param in enumerate(all_params)]
        ui.separator()
        with ui.row():
            ui.label('Filter').style('color: rgb(56 189 248)').tailwind.font_size('xl')
        with ui.row():
            ui.label('Apply a filter to the training data').tailwind.font_size('xs')
        with ui.row():
            state['filter_ui'] = ui.table(columns=columns, rows=rows, selection='multiple').classes('h-96 w-96')


@ui.refreshable
def create_extraction_ui() -> None:
    """Create the extraction UI elements."""
    if 'odds_types' in state:
        odds_types = state['odds_types']
        odds_types_mapping = {
            odds_type: " ".join([token.title() for token in odds_type.split('_')]) for odds_type in odds_types
        }
        ui.separator()
        with ui.row():
            ui.label('Extraction').style('color: rgb(56 189 248)').tailwind.font_size('xl')
        with ui.row():
            ui.label('Select the extraction parameters of the training data').tailwind.font_size('xs')
        with ui.grid(columns=2):
            state['odds_type_ui'] = ui.select(odds_types_mapping, value=odds_types[0], label='Odds type')
            state['drop_na_thres_ui'] = ui.number(min=0.0, max=1.0, step=0.05, value=0.0, label='Drop NA threshold')


@ui.refreshable
def create_data_ui() -> None:
    """Create the data UI elements."""
    if 'X_train' in state:
        with ui.row():
            ui.markdown('Training data').style('color: black').tailwind.font_size('5xl')
        with ui.row():
            max_n_rows = 10000
            with ui.column():
                columns = [
                    {
                        'name': col,
                        'label': " ".join([token.title() for token in re.split('__?', col)]),
                        'field': col,
                        'required': True,
                    }
                    for col in state['X_train'].columns
                ]
                ui.table(
                    columns,
                    state['X_train'][:max_n_rows].to_dict('records'),
                    pagination=5,
                    title='Input',
                ).classes('w-64')
            with ui.column():
                columns = [
                    {
                        'name': col,
                        'label': " ".join(
                            re.split('_', " (".join([token.title() for token in re.split('__', col)[1:]]) + ')'),
                        ),
                        'field': col,
                        'required': True,
                    }
                    for col in state['Y_train'].columns
                ]
                ui.table(
                    columns,
                    state['Y_train'][:max_n_rows].to_dict('records'),
                    pagination=5,
                    title='Output',
                ).classes('w-64')
            with ui.column():
                columns = [
                    {
                        'name': col,
                        'label': " ".join(
                            re.split('_', " (".join([token.title() for token in re.split('__', col)[2:]]) + ')'),
                        ),
                        'field': col,
                        'required': True,
                    }
                    for col in state['O_train'].columns
                ]
                ui.table(columns, state['O_train'][:max_n_rows].to_dict('records'), pagination=5, title='Odds').classes(
                    'w-64',
                )
        with ui.row():
            ui.markdown('Fixtures data').style('color: black').tailwind.font_size('5xl')
        with ui.row():
            with ui.column():
                columns = [
                    {
                        'name': col,
                        'label': " ".join([token.title() for token in re.split('__?', col)]),
                        'field': col,
                        'required': True,
                    }
                    for col in state['X_fix'].columns
                ]
                ui.table(columns, state['X_fix'][:max_n_rows].to_dict('records'), pagination=5, title='Input').classes(
                    'w-64',
                )
            with ui.column():
                columns = [
                    {
                        'name': col,
                        'label': " ".join(
                            re.split('_', " (".join([token.title() for token in re.split('__', col)[1:]]) + ')'),
                        ),
                        'field': col,
                        'required': True,
                    }
                    for col in state['Y_train'].columns
                ]
                ui.table(columns, [], pagination=5, title='Output').classes('w-64')
            with ui.column():
                columns = [
                    {
                        'name': col,
                        'label': " ".join(
                            re.split('_', " (".join([token.title() for token in re.split('__', col)[2:]]) + ')'),
                        ),
                        'field': col,
                        'required': True,
                    }
                    for col in state['O_fix'].columns
                ]
                ui.table(columns, state['O_fix'][:max_n_rows].to_dict('records'), pagination=5, title='Odds').classes(
                    'w-64',
                )


# Header
with ui.header(bordered=True).classes('bg-sky-400'), ui.element('q-toolbar'):  # noqa: SIM117
    with ui.element('q-toolbar-title').props('align=center'):
        ui.markdown('Sports-Betting').style('color: black').tailwind.font_size('6xl').font_weight('semibold')
        ui.markdown('Data extraction and model evaluation toolbox').tailwind.font_size('lg').font_weight('light')

# Left drawer
with ui.left_drawer(bordered=True, elevated=True) as left_drawer:
    left_drawer.props('width=450')
    with ui.row():
        ui.toggle(['Data', 'Betting'], value='Data')
    ui.separator()
    create_sport_ui()
    create_filter_ui()
    create_extraction_ui()
    ui.separator()
    create_control_ui()

# Main
create_data_ui()

ui.run()
