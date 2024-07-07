"""Data section of the GUI."""

import re
from pathlib import Path
from tempfile import TemporaryDirectory

from nicegui import run, ui

from sportsbet.datasets import SoccerDataLoader
from sportsbet.datasets._base import _BaseDataLoader
from sportsbet.gui._state import state

DATALOADERS = {
    'Soccer': SoccerDataLoader,
    'NBA': _BaseDataLoader,
    'NFL': _BaseDataLoader,
    'NHL': _BaseDataLoader,
}


def set_buttons_visibility(index: int) -> None:
    """Set the visibility of buttons."""
    buttons_ui = ['arrow_sport_ui', 'arrow_filter_ui', 'arrow_extraction_ui', 'download_ui']
    for button_ui in buttons_ui:
        state[button_ui].set_visibility(index == buttons_ui.index(button_ui))


async def select_sport() -> None:
    """Select the dataloader."""
    dataloader_name = state['sport_ui'].value
    if dataloader_name == 'Soccer':
        spinner = ui.spinner(size='lg')
        all_params = await run.io_bound(lambda: DATALOADERS[state['sport_ui'].value].get_all_params())
        spinner.set_visibility(False)
        params_names = next(tuple(param.keys()) for param in all_params)
        state['filter_columns'] = [
            {
                'name': 'id',
                'label': 'ID',
                'field': 'id',
                'required': True,
                'classes': 'hidden',
                'headerClasses': 'hidden',
            },
        ]
        state['filter_columns'] += [
            {'name': name, 'label': name.title(), 'field': name, 'required': False, 'sortable': True}
            for name in params_names
        ]
        state['filter_rows'] = [{**param, 'id': num + 1} for num, param in enumerate(all_params)]
        create_filter_ui.refresh()
        create_control_ui.refresh()
        set_buttons_visibility(1)
        state['sport_ui'].set_enabled(False)
    elif dataloader_name != 'Soccer' and dataloader_name is not None:
        ui.notify('Soccer is the only currently available sport.')
    else:
        ui.notify('Please select a sport to proceed.')


async def select_filter() -> None:
    """Select the filter to create dataloader."""
    if state['filter_ui'].selected:
        param_grid = [
            {name: [val] for name, val in param.items() if name != 'id'} for param in state['filter_ui'].selected
        ]
        state['dataloader'] = DATALOADERS[state['sport_ui'].value](param_grid=param_grid)  # type: ignore  # noqa: PGH003
        spinner = ui.spinner(size='lg')
        state['odds_types'] = await run.io_bound(lambda: state['dataloader'].get_odds_types())
        spinner.set_visibility(False)
        state['odds_types_mapping'] = {
            odds_type: " ".join([token.title() for token in odds_type.split('_')]) for odds_type in state['odds_types']
        }
        state['odds_types_mapping'].update({None: 'No Odds'})
        create_extraction_ui.refresh()
        create_control_ui.refresh()
        set_buttons_visibility(2)
        state['filter_ui'].props('disabled')
    else:
        ui.notify('Please select at least one row of filter table.')


async def select_extraction() -> None:
    """Select the extraction parameters of training data."""
    spinner = ui.spinner(size='lg')
    state['X_train'], state['Y_train'], state['O_train'] = await run.io_bound(
        lambda: state['dataloader'].extract_train_data(
            odds_type=state['odds_type_ui'].value,
            drop_na_thres=state['drop_na_thres_ui'].value,
        ),
    )
    state['X_fix'], state['Y_fix'], state['O_fix'] = await run.io_bound(
        lambda: state['dataloader'].extract_fixtures_data(),
    )
    spinner.set_visibility(False)
    create_data_ui.refresh()
    create_control_ui.refresh()
    set_buttons_visibility(3)
    state['odds_type_ui'].set_enabled(False)
    state['drop_na_thres_ui'].set_enabled(False)


def select_download() -> None:
    """Select the dowload button."""
    with TemporaryDirectory() as temp_dir:
        dest_path = Path(temp_dir) / 'dataloader.pkl'
        state['dataloader'].save(dest_path)
        with Path.open(Path(dest_path), 'rb') as dataloader_file:
            ui.download(dataloader_file.read(), 'dataloader.pkl')


@ui.refreshable
def create_sport_ui() -> None:
    """Create the sport UI elements."""
    if state['mode_ui'].value == 'Data':
        with ui.row():
            ui.label('Sport').style('color: rgb(56 189 248)').tailwind.font_size('xl')
        with ui.row():
            ui.label('Select one of the available sports').tailwind.font_size('xs')
        with ui.row():
            state['sport_ui'] = ui.radio(list(DATALOADERS)).props('inline')


@ui.refreshable
def create_filter_ui() -> None:
    """Create the filter UI elements."""
    if state['mode_ui'].value == 'Data' and 'filter_columns' in state and 'filter_rows' in state:
        ui.separator()
        with ui.row():
            ui.label('Filter').style('color: rgb(56 189 248)').tailwind.font_size('xl')
        with ui.row():
            ui.label('Apply a filter to the training data').tailwind.font_size('xs')
        with ui.row():
            state['filter_ui'] = ui.table(
                columns=state['filter_columns'],
                rows=state['filter_rows'],
                selection='multiple',
            ).classes('h-96 w-96')


@ui.refreshable
def create_extraction_ui() -> None:
    """Create the extraction UI elements."""
    if (
        state['mode_ui'].value == 'Data'
        and 'odds_types_mapping' in state
        and 'odds_types' in state
        and 'dataloader' in state
    ):
        ui.separator()
        with ui.row():
            ui.label('Extraction').style('color: rgb(56 189 248)').tailwind.font_size('xl')
        with ui.row():
            ui.label('Select the extraction parameters of the training data').tailwind.font_size('xs')
        with ui.grid(columns=2):
            state['odds_type_ui'] = ui.select(
                state['odds_types_mapping'],
                value=state['odds_types'][0],
                label='Odds type',
            )
            state['drop_na_thres_ui'] = ui.number(min=0.0, max=1.0, step=0.05, value=0.0, label='Drop NA threshold')


@ui.refreshable
def create_data_ui() -> None:
    """Create the data UI elements."""
    if (
        state['mode_ui'].value == 'Data'
        and 'X_train' in state
        and 'Y_train' in state
        and 'O_train' in state
        and 'X_fix' in state
        and 'Y_fix' in state
        and 'O_fix' in state
    ):
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
                state['X_train_ui'] = ui.table(
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
                state['Y_train_ui'] = ui.table(
                    columns,
                    state['Y_train'][:max_n_rows].to_dict('records'),
                    pagination=5,
                    title='Output',
                ).classes('w-64')
            with ui.column():
                columns = (
                    [
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
                    if state['O_train'] is not None
                    else []
                )
                rows = state['O_train'][:max_n_rows].to_dict('records') if state['O_train'] is not None else []
                state['O_train_ui'] = ui.table(columns, rows, pagination=5, title='Odds').classes(
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
                state['X_fix_ui'] = ui.table(
                    columns,
                    state['X_fix'][:max_n_rows].to_dict('records'),
                    pagination=5,
                    title='Input',
                ).classes(
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
                state['Y_fix_ui'] = ui.table(columns, [], pagination=5, title='Output').classes('w-64')
            with ui.column():
                columns = (
                    [
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
                    if state['O_fix'] is not None
                    else []
                )
                rows = state['O_fix'][:max_n_rows].to_dict('records') if state['O_fix'] is not None else []
                state['O_fix_ui'] = ui.table(columns, rows, pagination=5, title='Odds').classes(
                    'w-64',
                )


@ui.refreshable
def create_control_ui() -> None:
    """Create control UI elements."""
    if state['mode_ui'].value == 'Data':
        with ui.row():
            state['arrow_sport_ui'] = ui.button(icon='play_arrow', on_click=select_sport)
            state['arrow_filter_ui'] = ui.button(icon='play_arrow', on_click=select_filter)
            state['arrow_extraction_ui'] = ui.button(icon='play_arrow', on_click=select_extraction)
            state['download_ui'] = ui.button(icon='download', on_click=select_download)
