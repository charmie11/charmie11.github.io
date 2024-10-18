from bokeh.models import ColumnDataSource, CustomJS, Slider, Span
from bokeh.plotting import figure

from .cr_circuit import CIRCUIT_SETTINGS, Circuit


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
    sliders = {key: create_slider(key, setting) for key, setting in CIRCUIT_SETTINGS.items()}

    return sliders


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
    x_range = (-500, 6500)
    y_range = (-5, 55) if plot_data == 'v' else (-55, 55)
    plot = figure(
        title=title,
        width=600, height=400,
        x_range=x_range, y_range=y_range,
        x_axis_label="時間 [秒]", y_axis_label=y_axis_label,
        tools="hover,wheel_zoom,box_zoom,reset,save"
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

    plot.legend.location = "center_right"  if plot_data == 'v' else "bottom_right"

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
        // const times = Array.from(Array(num_samples).keys()).map(a => a * T / num_samples);
        const times = Array.from(Array(num_samples).keys()).map(a => a * T / (num_samples-1));
        const sigma_v = noise_voltage_slider.value;
        const sigma_i = noise_current_slider.value;

        let x = [];
        let v = [];
        let v_noisy = [];
        let i = [];
        let i_noisy = [];

        x = times;
        // モードの選択に基づいた計算
        if (radio_group.active === 0) {  // 充電モード
            v = x.map(a => E * (1.0 - Math.exp(-a / tau)));
            i = x.map(a => E * Math.exp(-a / tau) / R);
        } else {  // 放電モード
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

    """)


def create_download_callback(source, radio_button_group):
    """ ダウンロードボタンのコールバック """
    return CustomJS(
        args=dict(source=source, radio_group=radio_button_group),
        code="""
            // SheetJSをCDNからロード
            var script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
            script.onload = function() {
                // 最新のデータを取得
                const data = source.data;
                const E = data['E'][0];
                const R = data['R'][0];
                const C = data['C'][0];
                const sigma_v = data['sigma_v'][0];
                const sigma_i = data['sigma_i'][0];
                const t = data['t'];
                const v = data['v'];
                const v_noisy = data['v_noisy'];
                const i = data['i'];
                const i_noisy = data['i_noisy'];

                // ラジオボタンの選択状態を確認
                const selected_mode = radio_group.active === 0 ? 'charge' : 'discharge';

                // データを2次元配列に変換（Excelに対応）
                const rows = [
                    // ['電源電圧 [V]', '抵抗 [Ω]', '静電容量(真値) [F]', '電圧計測ノイズ強度', '電流計測ノイズ強度', '時間 [秒]', 'コンデンサの端子電圧 [V]', 'ノイズありコンデンサの端子電圧 [V]', '電流 [A]', 'ノイズあり電流 [A]']
                    ['E [V]', 'R [Ω]', 'C [F]', 'sigma_v', 'sigma_i', 't [秒]', 'V [V]', 'ln(V)', 'V* [V]', 'ln(V*)', 'I [A]', 'ln(-I)', 'I* [A]', 'ln(-I*)']
                ];
                // 1行目
                rows.push([E, R, C, sigma_v, sigma_i, t[0], v[0], '', v_noisy[0], '', i[0], '', i_noisy[0], '']);
                for (let n = 1; n < t.length; n++) {
                    rows.push(['', '', '', '', '', t[n], v[n], '', v_noisy[n], '', i[n], '', i_noisy[n], '']);
                }

                // xlsxファイルの作成
                var ws = XLSX.utils.aoa_to_sheet(rows);  // 2次元配列からシートを作成
                var wb = XLSX.utils.book_new();  // 新しいワークブック作成
                XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');  // ワークブックにシートを追加

                // ファイル名の設定
                const fileName = selected_mode === 'charge' ? 'charge_data.xlsx' : 'discharge_data.xlsx';

                // xlsxファイルをダウンロード
                XLSX.writeFile(wb, fileName);  // xlsxファイルをダウンロード
            };
            document.head.appendChild(script);  // スクリプトをHTMLに追加
        """
    )
