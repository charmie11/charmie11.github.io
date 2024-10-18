import os
import sys
sys.path.append('.')

from bokeh.io import output_file
from bokeh.layouts import column, row
from bokeh.models import Button, RadioButtonGroup, Span
from bokeh.plotting import show

from src.ccs.simulator_components import initialize_sliders, create_initial_source, create_plot, create_callback, create_download_callback


def main():
    """ メイン関数 """

    # スライダーとデータの初期化
    sliders = initialize_sliders()
    source = create_initial_source(sliders)

    # プロットの作成
    plot_v = create_plot(source, 'v')
    plot_i = create_plot(source, 'i')
    plot_i.x_range = plot_v.x_range

    # 線の追加
    line_v_limit = Span(location=sliders['E'].value, dimension='width', line_color='black', line_dash='dashed', line_width=1)
    line_i_limit = Span(location=-sliders['E'].value/sliders['R'].value, dimension='width', line_color='black', line_dash='dashed', line_width=1)

    plot_v.add_layout(line_v_limit)
    plot_i.add_layout(line_i_limit)

    # ラジオボタンの設定
    radio_button_group = RadioButtonGroup(labels=["充電", "放電"], active=1)

    # コールバックの設定
    callback = create_callback(source, sliders, radio_button_group, plot_v, plot_i, line_v_limit, line_i_limit)
    for slider in sliders.values():
        slider.js_on_change('value', callback)
    radio_button_group.js_on_change('active', callback)

    # ダウンロードボタンの設定
    button_download = Button(label="ダウンロード", button_type="success", background='red')
    button_download.js_on_click(create_download_callback(source, radio_button_group))

    # レイアウトの設定と表示
    from bokeh.models import Div

    sheetjs_script = Div(text="""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.16.2/xlsx.full.min.js"></script>
    """, width=0, height=0)  # サイズを最小限にする

    # left: settings, right: plot
    layout = row(
        sheetjs_script,
        column(
            sliders['E'], sliders['voltage_noise'],
            sliders['R'], sliders['current_noise'],
            sliders['C'],
            sliders['T'], sliders['N'],
            radio_button_group,
            button_download,
            sizing_mode="fixed", width=200, height=600,
        ),
        column(plot_v, plot_i),
    )
    filename = "app.html"
    output_file(filename, title="CR直列回路シミュレータ", mode="inline")

    show(layout)


if __name__ == "__main__":
    main()
