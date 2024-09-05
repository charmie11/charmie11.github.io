import os
from bokeh.io import output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, CustomJS, Slider, Button
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
plot = figure(width=600, height=400)
plot.scatter('x', 'y', source=source)

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

num_padding = len(source.data['x']) - 1
padding = [''] * num_padding
button_download = Button(label="ダウンロード", button_type="success")
callback_download = CustomJS(
    args=dict(source=
    ColumnDataSource(data={
        '電源電圧 [V]': [source.data['V'][0]] + padding,
        '抵抗 [Ω]': [source.data['R'][0]] + padding,
        '静電容量(真値) [F]': [source.data['C'][0]] + padding,
        '時間 [秒]': source.data['x'],
        'コンデンサの端子電圧 [V]': source.data['y'],
    })),
    code=open(os.path.join(os.path.dirname(__file__), "download.js")).read()
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
