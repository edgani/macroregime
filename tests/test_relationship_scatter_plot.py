import pandas as pd
import numpy as np
import plotly.express as px


def _plot_frame(index_name):
    idx = pd.date_range('2020-01-31', periods=36, freq='ME')
    idx.name = index_name
    d = pd.DataFrame({
        'factor_value': np.linspace(-2, 2, 36),
        'forward_return': np.linspace(-.1, .15, 36),
    }, index=idx)
    plot_d = d[['factor_value', 'forward_return']].copy()
    plot_d.index = pd.to_datetime(plot_d.index, errors='coerce')
    plot_d = plot_d.loc[plot_d.index.notna()].copy()
    plot_d.index.name = 'date'
    plot_d = plot_d.reset_index()
    fig = px.scatter(plot_d, x='factor_value', y='forward_return', hover_data=['date'])
    return plot_d, fig


def test_scatter_index_names_are_normalized():
    for name in [None, 'DATE', 'observation_date', 'foo']:
        frame, fig = _plot_frame(name)
        assert 'date' in frame.columns
        assert len(fig.data) == 1
