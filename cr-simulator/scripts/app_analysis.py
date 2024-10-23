import os
import sys
sys.path.append('.')

from bokeh.io import output_file
from bokeh.layouts import column, row
from bokeh.models import Button, RadioButtonGroup, Span
from bokeh.plotting import show
from bokeh.models import Div

from bokeh.models import ColumnDataSource, TableColumn, DataTable

from src.ccs.simulator_components import initialize_sliders, create_initial_source, create_plot, create_callback, create_download_results_callback, create_analysis_callback


def main():
    """ メイン関数 """

    # スライダーとデータの初期化
    sliders = initialize_sliders()
    source = create_initial_source(sliders)

    # プロットの作成
    plot_v = create_plot(source, 'v')
    plot_i = create_plot(source, 'i')
    plot_v.width = plot_i.width = 400
    plot_v.height = plot_i.height = 300
    plot_i.x_range = plot_v.x_range

    # 線の追加
    line_v_limit = Span(location=sliders['E'].value, dimension='width', line_color='black', line_dash='dashed', line_width=1)
    line_i_limit = Span(location=-sliders['E'].value/sliders['R'].value, dimension='width', line_color='black', line_dash='dashed', line_width=1)

    plot_v.add_layout(line_v_limit)
    plot_i.add_layout(line_i_limit)

    # 解析結果のまとめ
    columns = ["E", "R", "C", "sigma_v", "sigma_i", "T", "N", "T'", "N'", "E'", "R'", "C'"]
    data = {c: [] for c in columns}
    results = ColumnDataSource(data=data)

    # ラジオボタンの設定
    radio_button_group = RadioButtonGroup(labels=["充電", "放電"], active=1)

    # コールバックの設定
    callback = create_callback(source, sliders, radio_button_group, plot_v, plot_i, line_v_limit, line_i_limit)
    for slider in sliders.values():
        slider.js_on_change('value', callback)

    # 解析ボタンの設定
    button_analysis = Button(label="解析", button_type="success", background='red')
    button_analysis.js_on_click(create_analysis_callback(source, results))

    # ダウンロードボタンの設定
    button_download = Button(label="ダウンロード", button_type="success", background='red')
    button_download.js_on_click(create_download_results_callback(results))

    # レイアウトの設定と表示
    sheetjs_script = Div(
        text="""<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.16.2/xlsx.full.min.js"></script>""",
        width=0, height=0
    )

    columns = [TableColumn(field=c, title=c) for c in columns]
    result_table = DataTable(source=results, columns=columns)

    layout = column(
        sheetjs_script,
        row(sliders['E'], sliders['voltage_noise']),
        row(sliders['R'], sliders['current_noise']),
        row(sliders['C']),
        row(sliders['T'], sliders['N']),
        row(button_analysis, button_download),
        row(plot_v, plot_i),
        result_table
    )
    filename = "app_analysis.html"
    output_file(filename, title="CR直列回路シミュレータ", mode="inline")

    show(layout)


if __name__ == "__main__":
    main()
