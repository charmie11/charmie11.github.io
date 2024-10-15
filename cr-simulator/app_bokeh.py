from bokeh.io import output_file
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, PrintfTickFormatter, CustomJS, Slider, Button, RadioButtonGroup, Span, TextInput
from bokeh.plotting import figure, show
from cr_circuit import Circuit, settings


def create_slider(key, setting):
    """ スライダーを作成するヘルパー関数 """
    return Slider(
        start=setting['min'],
        end=setting['max'],
        value=setting['default'],
        step=setting['step'],
        title=setting['text'],
    )


def initialize_sliders():
    """ 設定からスライダーを初期化 """
    sliders = {key: create_slider(key, setting) for key, setting in settings.items()}

    # 周期スライダーの更新コールバック
    update_slider_max = CustomJS(
        args=dict(
            E=sliders['E'],
            R=sliders['R'],
            C=sliders['C'],
            T=sliders['T'],
            sigma_v=sliders['voltage_noise'],
            sigma_i=sliders['current_noise'],
        ),
        code="""
        // 周期の横軸を変更
        const tau = R.value * C.value;
        T.start = 0.1 * tau;
        T.end = 15.0 * tau;
        T.step = 0.1 * tau;
        T.value = Math.min(Math.max(T.value, T.start), T.end);
        T.change.emit();
        
        // 電圧計測ノイズの横軸を変更
        sigma_v.end = 0.10 * E.value;
        sigma_v.step = 0.01 * sigma_v.end;
        sigma_v.value = Math.min(Math.max(sigma_v.value, sigma_v.start), sigma_v.end);
        sigma_v.change.emit();

        // 電龍計測ノイズの横軸を変更
        const i_max = E.value / R.value;
        sigma_i.end = 0.10 * i_max;
        sigma_i.step = 0.01 * sigma_i.end;
        sigma_i.value = Math.min(Math.max(sigma_i.value, sigma_i.start), sigma_i.end);
        sigma_i.change.emit();
        """
    )

    # R, C の値に応じて周期のスライダーを更新
    sliders['E'].js_on_change('value', update_slider_max)
    sliders['R'].js_on_change('value', update_slider_max)
    sliders['C'].js_on_change('value', update_slider_max)

    return sliders


def initialize_texts(E, R, C):
    texts = {
        # "tau": TextInput(value=f"{R*C}", title="R*C: ", styles={'text_font_size': '13pt'}),
        # "i_max": TextInput(value=f"{E/R}", title="E/R: ", styles={'font-size': '13pt'}, css_classes=["custom-input"]),
        "tau": TextInput(value=f"{R*C}", title="R*C: "),
        "i_max": TextInput(value=f"{E/R}", title="E/R: "),
    }
    return texts


def create_initial_source(sliders):
    """ 初期の ColumnDataSource を作成 """
    E, T, R, C = sliders['E'].value, sliders['T'].value, sliders['R'].value, sliders['C'].value
    circuit = Circuit(E, T, R, C)
    df = circuit.measure(num_samples=sliders['N'].value)
    return ColumnDataSource(data={
        't': df['時間 [秒]'].tolist(),
        'v': df['コンデンサの端子電圧 [V]'].tolist(),
        'v_noisy': df['コンデンサの端子電圧 [V]'].tolist(),
        'i': df['電流 [A]'].tolist(),
        'i_noisy': df['電流 [A]'].tolist(),
        'E': [E] * len(df),
        'R': [R] * len(df),
        'C': [C] * len(df),
        'sigma_v': [0.0] * len(df),
        'sigma_i': [0.0] * len(df),
    })


def create_plot(source, plot_data='v'):
    assert plot_data in ['v', 'i']

    size = 15
    title = "コンデンサの端子電圧の遷移" if plot_data == 'v' else "電流の遷移"
    y_axis_label = "電圧 [V]" if plot_data == 'v' else "電流 [A]"
    plot = figure(
        title=title,
        width=600, height=400,
        x_axis_label="時間 [秒]", y_axis_label=y_axis_label,
        tools="pan,wheel_zoom,box_zoom,reset"
    )

    plot.scatter(
        't', f'{plot_data}_noisy', source=source, legend_label="計測ノイズあり",
        marker='x', size=size, color="blue",
    )
    plot.scatter(
        't', f'{plot_data}', source=source, legend_label="計測ノイズなし",
        marker='circle', fill_alpha=0, size=size, color="red",
    )

    line_h = Span(location=0, dimension='width', line_color='black', line_width=1)
    line_v = Span(location=0, dimension='height', line_color='black', line_width=1)

    plot.add_layout(line_h)
    plot.add_layout(line_v)

    plot.xaxis.axis_label_text_font_size = "13pt"
    plot.yaxis.axis_label_text_font_size = "13pt"
    plot.xaxis.major_label_text_font_size = "11pt"
    plot.yaxis.major_label_text_font_size = "11pt"

    plot.legend.location = "center_right"

    return plot


def create_callback(source, sliders, radio_button_group, plot_v, plot_i, line_v_limit, line_i_limit):
    """ プロット更新の JavaScript コールバック """
    return CustomJS(args=dict(
        source=source,
        voltage=sliders['E'],
        period=sliders['T'],
        resistance=sliders['R'],
        capacitance=sliders['C'],
        samples=sliders['N'],
        noise_voltage_slider=sliders['voltage_noise'],
        noise_current_slider=sliders['current_noise'],
        radio_group=radio_button_group,
        # texts=texts,
        plot_v=plot_v,
        plot_i=plot_i,
        line_v_limit=line_v_limit,
        line_i_limit=line_i_limit,
    ), code="""
        // 正規分布を生成する関数 (Box-Muller法)
        function generateGaussianNoise(mean, stdDev) {
            let u1 = Math.random();
            let u2 = Math.random();
            let z0 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
            return mean + z0 * stdDev;
        }

        // 値の取得
        const E = voltage.value;
        const T = period.value;
        const R = resistance.value;
        const C = capacitance.value;
        const num_samples = samples.value;
        const tau = R * C;
        const times = Array.from(Array(num_samples).keys()).map(a => a * T / num_samples);
        const sigma_v = noise_voltage_slider.value;
        const sigma_i = noise_current_slider.value;

        let x = [];
        let v = [];
        let v_noisy = [];
        let i = [];
        let i_noisy = [];

        // モードの選択に基づいた計算
        if (radio_group.active === 0) {  // 充電モード
            x = times;
            v = x.map(a => E * (1.0 - Math.exp(-a / tau)));
            i = x.map(a => E * Math.exp(-a / tau) / R);
        } else {  // 放電モード
            x = times;
            v = x.map(a => E * Math.exp(-a / tau));
            i = x.map(a => -E * Math.exp(-a / tau) / R);
        }

        // ノイズの追加（正規分布に基づくノイズ生成）
        const noise_v = v.map(() => generateGaussianNoise(0, sigma_v));
        v_noisy = v.map((a, j) => a + noise_v[j]);
        const noise_i = v.map(() => generateGaussianNoise(0, sigma_i));
        i_noisy = i.map((a, j) => a + noise_i[j]);

        // データの更新
        source.data = {
            t: x,
            v: v,
            v_noisy: v_noisy,
            i: i,
            i_noisy: i_noisy,
            E: Array(x.length).fill(E),
            R: Array(x.length).fill(R),
            C: Array(x.length).fill(C),
            sigma_v: Array(x.length).fill(sigma_v),
            sigma_i: Array(x.length).fill(sigma_i),
        };
        source.change.emit();

        // 電圧の上限を表示
        line_v_limit.location = E;
        plot_v.change.emit();

        // 電流の上限・下限を表示
        if (radio_group.active === 0) {  // 充電モード
            line_i_limit.location = E/R;
        } else {  // 放電モード
            line_i_limit.location = -E/R;
        }
        plot_i.change.emit();

        // // テキストボックスの値を更新
        // texts['tau'].value = `${tau.toFixed(2)}`;  // R*Cの計算結果を表示
        // texts['i_max'].value = `${(E/R).toFixed(2)}`;  // E/Rの計算結果を表示

    """)


def create_download_callback(source, radio_button_group):
    """ ダウンロードボタンのコールバック """
    return CustomJS(
        args=dict(source=source, radio_group=radio_button_group),
        code="""
        // 最新のデータを取得
        const data = source.data;
        const E = data['E'][0].toFixed(15);
        const R = data['R'][0].toFixed(15);
        const C = data['C'][0].toFixed(15);
        const sigma_v = data['sigma_v'][0].toFixed(15);
        const sigma_i = data['sigma_i'][0].toFixed(15);
        const t = data['t'];
        const v = data['v'];
        const v_noisy = data['v_noisy'];
        const i = data['i'];
        const i_noisy = data['i_noisy'];

        // ラジオボタンの選択状態を確認
        const selected_mode = radio_group.active === 0 ? 'charge' : 'discharge';

        // CSV データの生成
        const csv = ['電源電圧 [V],抵抗 [Ω],静電容量(真値) [F],電圧計測ノイズ強度,電流計測ノイズ強度,時間 [秒],コンデンサの端子電圧 [V],ノイズありコンデンサの端子電圧 [V],電流 [A],ノイズあり電流 [A]'];
        // 1行目
        csv.push([E, R, C, sigma_v, sigma_i, t[0].toFixed(15), v[0].toFixed(15), v_noisy[0].toFixed(15), i[0].toFixed(15), i_noisy[0].toFixed(15)].join(','));
        for (let n = 1; n < t.length; n++) {
            csv.push(['', '', '', '', '', t[n].toFixed(15), v[n].toFixed(15), v_noisy[n].toFixed(15), i[n].toFixed(15), i_noisy[n].toFixed(15)].join(','));
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
    plot_v = create_plot(source, 'v')
    plot_i = create_plot(source, 'i')

    # 線の追加
    line_v_limit = Span(location=sliders['E'].value, dimension='width', line_color='black', line_dash='dashed', line_width=1)
    line_i_limit = Span(location=sliders['E'].value/sliders['R'].value, dimension='width', line_color='black', line_dash='dashed', line_width=1)

    plot_v.add_layout(line_v_limit)
    plot_i.add_layout(line_i_limit)

    # ラジオボタンの設定
    radio_button_group = RadioButtonGroup(labels=["充電", "放電"], active=0)

    # コールバックの設定
    callback = create_callback(source, sliders, radio_button_group, plot_v, plot_i, line_v_limit, line_i_limit)
    for slider in sliders.values():
        slider.js_on_change('value', callback)
    radio_button_group.js_on_change('active', callback)

    # ダウンロードボタンの設定
    button_download = Button(label="ダウンロード", button_type="success")
    button_download.js_on_click(create_download_callback(source, radio_button_group))

    # レイアウトの設定と表示
    # top: settings, bottom: plot
    # layout = column(
    #     row(sliders['E'], sliders['voltage_noise']),
    #     row(sliders['R'], sliders['current_noise']),
    #     row(sliders['C']),
    #     row(sliders['T'], sliders['N']),
    #     radio_button_group,
    #     button_download,
    #     # row(plot_v, plot_i, sizing_mode='scale_width'),
    #     row(plot_v, plot_i),
    # )
    # # left: settings, right: plot
    # layout = column(
    #     row(column(sliders['E'], sliders['voltage_noise']), plot_v),
    #     row(column(sliders['R'], sliders['current_noise']), plot_i),
    #     row(sliders['C']),
    #     row(sliders['T'], sliders['N']),
    #     radio_button_group,
    #     button_download,
    # )
    # left: settings, right: plot
    layout = row(
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
    output_file(filename, title="CR直列回路シミュレータ")

    show(layout)


if __name__ == "__main__":
    main()
