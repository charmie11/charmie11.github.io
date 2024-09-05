import os
from bokeh.io import output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, PrintfTickFormatter, CustomJS, Slider, Button, RadioButtonGroup
from bokeh.plotting import figure, show
from cr_circuit import Circuit, settings


def create_slider(key, setting):
    """ スライダーを作成するヘルパー関数 """
    return Slider(
        start=setting['min'],
        end=setting['max'],
        value=setting['default'],
        step=setting['step'],
        title=setting['text']
    )


def initialize_sliders():
    """ 設定からスライダーを初期化 """
    sliders = {key: create_slider(key, setting) for key, setting in settings.items()}

    # 周期スライダーの更新コールバック
    update_slider_period = CustomJS(
        args=dict(
            resistance=sliders['R'],
            capacitance=sliders['C'],
            period=sliders['T']
        ),
        code="""
        const tau = resistance.value * capacitance.value;
        period.start = 0.1 * tau;
        period.end = 15.0 * tau;
        period.value = Math.min(Math.max(period.value, period.start), period.end);
        period.step = 0.1 * tau;
        period.change.emit();
        """
    )

    # R, C の値に応じて周期のスライダーを更新
    sliders['R'].js_on_change('value', update_slider_period)
    sliders['C'].js_on_change('value', update_slider_period)
    return sliders


def create_initial_source(sliders):
    """ 初期の ColumnDataSource を作成 """
    V, T, R, C = sliders['V'].value, sliders['T'].value, sliders['R'].value, sliders['C'].value
    circuit = Circuit(V, T, R, C)
    df = circuit.measure(num_samples=sliders['N'].value)
    df = df.head(len(df)//2)
    return ColumnDataSource(data={
        'x': df['時間 [秒]'].tolist(),
        'y': df['コンデンサの端子電圧 [V]'].tolist(),
        'V': [V] * len(df),
        'R': [R] * len(df),
        'C': [C] * len(df),
    })


def create_plot(source):
    """ プロットを作成 """
    plot = figure(
        width=600, height=400,
        title="コンデンサの端子電圧の遷移",
        x_axis_label="時間 [秒]", y_axis_label="電圧 [V]",
        tools="pan,wheel_zoom,box_zoom,reset"
    )
    plot.scatter('x', 'y', source=source)
    plot.xaxis.formatter = PrintfTickFormatter(format="%.1f")
    plot.yaxis.formatter = PrintfTickFormatter(format="%.1f")
    return plot


def create_callback(source, sliders, radio_button_group):
    """ プロット更新の JavaScript コールバック """
    return CustomJS(args=dict(
        source=source,
        voltage=sliders['V'],
        period=sliders['T'],
        resistance=sliders['R'],
        capacitance=sliders['C'],
        samples=sliders['N'],
        radio_group=radio_button_group
    ), code="""
        // 値の取得
        const V = voltage.value;
        const T = period.value;
        const R = resistance.value;
        const C = capacitance.value;
        const num_samples = samples.value;
        const tau = R * C;
        const times = Array.from(Array(num_samples).keys()).map(i => i * T / num_samples);

        let x = [];
        let y = [];

        // モードの選択に基づいた計算
        if (radio_group.active === 0) {  // 充電モード
            x = times;
            y = times.map(t => V * (1.0 - Math.exp(-t / tau)));
            y = y.map(v => Math.min(v, V));  // 最大値でクリップ
        } else {  // 放電モード
            x = times;
            y = times.map(t => V * Math.exp(-t / tau));
            y = y.map(v => Math.max(v, 0));  // 最小値でクリップ
        }

        // データの更新
        source.data = {
            x: x,
            y: y,
            V: Array(x.length).fill(V),
            R: Array(x.length).fill(R),
            C: Array(x.length).fill(C)
        };
        source.change.emit();
    """)


def create_download_callback(source, radio_button_group):
    """ ダウンロードボタンのコールバック """
    return CustomJS(
        args=dict(source=source, radio_group=radio_button_group),
        code="""
        // 最新のデータを取得
        const data = source.data;
        const V = data['V'][0].toFixed(15);
        const R = data['R'][0].toFixed(15);
        const C = data['C'][0].toFixed(15);
        const x = data['x'];
        const y = data['y'];

        // ラジオボタンの選択状態を確認
        const selected_mode = radio_group.active === 0 ? 'charge' : 'discharge';

        // CSV データの生成
        const csv = ['電源電圧 [V],抵抗 [Ω],静電容量(真値) [F],時間 [秒],コンデンサの端子電圧 [V]'];
        // 1行目
        csv.push([V, R, C, x[0].toFixed(15), y[0].toFixed(15)].join(','));
        for (let i = 1; i < x.length; i++) {
            csv.push(['', '', '', x[i].toFixed(15), y[i].toFixed(15)].join(','));
        }
        const csvContent = csv.join('\\n');

        // ファイル名の設定
        const fileName = selected_mode === 'charge' ? 'charge_data.csv' : 'discharge_data.csv';

        // CSV ファイルをダウンロード
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = fileName;
        link.click();
        """
    )


def main():
    """ メイン関数 """
    # スライダーとデータの初期化
    sliders = initialize_sliders()
    source = create_initial_source(sliders)

    # プロットの作成
    plot = create_plot(source)

    # ラジオボタンの設定
    radio_button_group = RadioButtonGroup(labels=["充電", "放電"], active=0)

    # コールバックの設定
    callback = create_callback(source, sliders, radio_button_group)
    for slider in sliders.values():
        slider.js_on_change('value', callback)
    radio_button_group.js_on_change('active', callback)

    # ダウンロードボタンの設定
    button_download = Button(label="ダウンロード", button_type="success")
    button_download.js_on_click(create_download_callback(source, radio_button_group))

    # レイアウトの設定と表示
    layout = column(
        row(
            column(sliders['V'], sliders['R'], sliders['C']),
            column(sliders['T'], sliders['N'])
        ),
        radio_button_group,
        button_download,
        plot
    )

    output_file("app.html", title="CR直列回路シミュレータ")
    show(layout)


if __name__ == "__main__":
    main()
