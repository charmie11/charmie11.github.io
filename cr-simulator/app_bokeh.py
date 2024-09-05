import os
from bokeh.io import output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, PrintfTickFormatter, CustomJS, Slider, Button
from bokeh.plotting import figure, show

from cr_circuit import Circuit, settings


# スライダーの設定
sliders = {}
for key, setting in settings.items():
    sliders[key] = Slider(
        start=setting['min'], end=setting['max'], value=setting['default'], step=setting['step'], title=setting['text'])
# R, Cの値によって周期の最小・最大値を変更
update_slider_period = CustomJS(
    args=dict(
        resistance=sliders['R'], capacitance=sliders['C'], period=sliders['T']
    ),
    code="""
    const tau = resistance.value * capacitance.value;
    period.start = 0.1 * tau
    period.end = 15.0 * tau
    period.value = Math.min(Math.max(period.value, period.start), period.end)
    period.step = 0.1 * tau
    period.change.emit();
""")

# `resistance_slider`の値が変更されたときに`capacitance_slider`の上限を更新
sliders['R'].js_on_change('value', update_slider_period)
sliders['C'].js_on_change('value', update_slider_period)

# データの初期設定
V, T, R, C = sliders['V'].value, sliders['T'].value, sliders['R'].value, sliders['C'].value
circuit = Circuit(V, T, R, C)
df = circuit.measure(num_samples=sliders['N'].value)
times = df['時間 [秒]'].tolist()
V_c = df['コンデンサの端子電圧 [V]'].tolist()
num_data = len(times)

source = ColumnDataSource(data={
    'x': times,
    'y': V_c,
    'V': [V]*num_data,
    'R': [R]*num_data,
    'C': [C]*num_data,
})
# プロットの設定
plot = figure(
    width=600, height=400,
    title="コンデンサの端子電圧の遷移",
    x_axis_label="時間 [秒]", y_axis_label="電圧 [V]",
    tools="pan,wheel_zoom,box_zoom,reset")
plot.scatter('x', 'y', source=source)
plot.xaxis.formatter = PrintfTickFormatter(format="%.1f")
plot.yaxis.formatter = PrintfTickFormatter(format="%.1f")

# JavaScriptコールバック
callback = CustomJS(args=dict(source=source,
                              voltage=sliders['V'],
                              period=sliders['T'],
                              resistance=sliders['R'],
                              capacitance=sliders['C'],
                              samples=sliders['N']),
                    code="""
    const V = voltage.value;
    const T = period.value;
    const R = resistance.value;
    const C = capacitance.value;
    const num_samples = samples.value;
    
    const tau = R * C;
    const times = Array.from(Array(2 * num_samples).keys()).map(i => i * T / (2 * num_samples));
    
    // 充電の計算
    const v_charge = times.slice(0, num_samples).map(t => V * (1.0 - Math.exp(-t / tau)));
    const v_charge_clamped = v_charge.map(v => Math.min(v, V));
    
    // 放電の計算
    const v_offset = V - v_charge_clamped[v_charge_clamped.length - 1];
    const time_offset = times[num_samples - 1];
    const v_discharge = times.slice(num_samples).map(t => V * Math.exp(-(t - time_offset) / tau) - v_offset);
    const v_discharge_clamped = v_discharge.map(v => Math.max(v, 0));
    
    // データの設定
    const x = times.slice(0, -1);
    const v_all = v_charge_clamped.concat(v_discharge_clamped);
    const y = v_all.slice(0, -1);

    // 更新するデータの設定
    source.data = {
        x: x,
        y: y,
        V: Array(x.length).fill(V),
        R: Array(x.length).fill(R),
        C: Array(x.length).fill(C)
    };
    source.change.emit();
""")

# スライダーの変更時にコールバックを呼び出す
for slider in sliders.values():
    slider.js_on_change('value', callback)

# データのダウンロード
button_download = Button(label="ダウンロード", button_type="success")
callback_download = CustomJS(
    args=dict(source=source),
    code="""
    // 最新のデータを取得
    const data = source.data;
    const V = data['V'][0].toFixed(15);
    const R = data['R'][0].toFixed(15);
    const C = data['C'][0].toFixed(15);
    const x = data['x'];
    const y = data['y'];

    // CSVデータの生成
    const csv = ['電源電圧 [V],抵抗 [Ω],静電容量(真値) [F],時間 [秒],コンデンサの端子電圧 [V]'];
    // 1行目
    csv.push([V, R, C, x[0].toFixed(15), y[0].toFixed(15)].join(','));
    for (let i = 1; i < x.length; i++) {
        csv.push(['', '', '', x[i].toFixed(15), y[i].toFixed(15)].join(','));
    }
    const csvContent = csv.join('\\n');

    // CSVファイルをダウンロード
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'cr-simulator.csv';
    link.click();
"""
)
button_download.js_on_click(callback_download)

# レイアウトの設定
layout = column(
    row(
        column(sliders['V'], sliders['R'], sliders['C']),
        column(sliders['T'], sliders['N'])
    ),
    button_download,
    plot
)

# プロットを表示
output_file("app.html", title="CR直列回路シミュレータ")
show(layout)
