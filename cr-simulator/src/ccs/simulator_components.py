import numpy as np

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
    sigma_v, sigma_i = sliders['voltage_noise'].value, sliders['current_noise'].value
    circuit = Circuit(E, T, R, C)
    N = sliders['N'].value
    df = circuit.measure(num_samples=N)
    v = df['コンデンサの端子電圧 [V]'].to_numpy()
    v_noisy = v + np.random.normal(0.0, sigma_v, N)
    i = df['電流 [A]'].to_numpy()
    i_noisy = i + np.random.normal(0.0, sigma_i, N)
    return ColumnDataSource(data={
        't': df['時間 [秒]'].tolist(),
        # 'v': df['コンデンサの端子電圧 [V]'].tolist(),
        # 'v_noisy': df['コンデンサの端子電圧 [V]'].tolist(),
        # 'i': df['電流 [A]'].tolist(),
        # 'i_noisy': df['電流 [A]'].tolist(),
        'v': v.tolist(),
        'v_noisy': v_noisy.tolist(),
        'i': i.tolist(),
        'i_noisy': i_noisy.tolist(),
        'E': [E] * len(df),
        'R': [R] * len(df),
        'C': [C] * len(df),
        'sigma_v': [sigma_v] * len(df),
        'sigma_i': [sigma_i] * len(df),
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
        't', f'{plot_data}_noisy', source=source, legend_label="計測値",
        marker='x', size=size, color="blue",
    )
    plot.scatter(
        't', f'{plot_data}', source=source, legend_label="理論値",
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

    plot.legend.location = "center_right" if plot_data == 'v' else "bottom_right"

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
                    ['電源電圧 E [V]', '抵抗 R [Ω]', '静電容量 C [F]', '電圧計測ノイズ強度 sigma_v', '電流計測ノイズ強度 sigma_i', '時間 t [秒]', 'コンデンサの端子電圧 (理論値) V [V]', 'ln(V)', '電流 (理論値) I [A]', 'ln(I)', 'コンデンサの端子電圧 (計測値) V* [V]', 'ln(V*)', '電流 (計測値) I* [A]', 'ln(I*)']
                    // ['E [V]', 'R [Ω]', 'C [F]', 'sigma_v', 'sigma_i', 't [秒]', 'V [V]', 'ln(V)', 'V* [V]', 'ln(V*)', 'I [A]', 'ln(-I)', 'I* [A]', 'ln(-I*)']
                ];
                // 1行目
                // rows.push([E, R, C, sigma_v, sigma_i, t[0], v[0], '', v_noisy[0], '', i[0], '', i_noisy[0], '']);
                rows.push([E, R, C, sigma_v, sigma_i, t[0], v[0], '', i[0], '', v_noisy[0], '', i_noisy[0], '']);
                for (let n = 1; n < t.length; n++) {
                    // rows.push(['', '', '', '', '', t[n], v[n], '', v_noisy[n], '', i[n], '', i_noisy[n], '']);
                    rows.push(['', '', '', '', '', t[n], v[n], '', i[n], '', v_noisy[n], '', i_noisy[n], '']);
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


def create_analysis_callback(source, results):
    return CustomJS(
        args=dict(source=source, results=results),
        code="""
            // データを取得
            const data = source.data;

            const t = data['t'];
            const E = data['E'][0];
            const R = data['R'][0];
            const C = data['C'][0];
            const tau = R * C;
            const v_noisy = data['v_noisy'];
            const i_noisy = data['i_noisy'];
            const N = t.length;
            const T = t[N-1];

            const filtered_t = [];
            const filtered_ln_v = [];
            const filtered_ln_i = [];

            let n = 0; // ループカウンタを初期化
            while (n < N) {
                if ((v_noisy[n] > 0) && (i_noisy[n] < 0)) {
                    filtered_t.push(t[n]);
                    filtered_ln_v.push(Math.log(v_noisy[n]));
                    filtered_ln_i.push(Math.log(-i_noisy[n]));
                } else {
                    break; // 条件を満たさない場合はループを終了
                }
                n++; // ループカウンタをインクリメント
            }

            const N_hat = filtered_t.length;
            const T_hat = filtered_t[N_hat-1];

            if (N_hat < 2) {
                console.log("Not enough data points for fitting.");
                return;
            }

            // xとln(y)の平均を計算
            const mean_t = filtered_t.reduce((sum, value) => sum + value, 0) / N_hat;
            const mean_ln_v = filtered_ln_v.reduce((sum, value) => sum + value, 0) / N_hat;
            const mean_ln_i = filtered_ln_i.reduce((sum, value) => sum + value, 0) / N_hat;

            // 傾き a の計算 (最小二乗法)
            let num_v = 0;  // 分子
            let num_i = 0;  // 分子
            let den = 0;    // 分母
            for (let n = 0; n < N_hat; n++) {
                num_v += (filtered_t[n] - mean_t) * (filtered_ln_v[n] - mean_ln_v);
                num_i += (filtered_t[n] - mean_t) * (filtered_ln_i[n] - mean_ln_i);
                den += (filtered_t[n] - mean_t) ** 2;
            }

            if (den === 0) {
                console.log("Denominator is zero, cannot compute slope.");
                return; // ゼロ除算を防ぐために終了
            }

            const a_v = num_v / den;
            const b_v = mean_ln_v - a_v * mean_t;
            const a_i = num_i / den;
            const b_i = mean_ln_i - a_i * mean_t;

            const E_hat = Math.exp(b_v);
            const R_hat = Math.exp(b_v - b_i);
            const C_hat = -1.0 / (R_hat * a_v);
            // const C_hat_v = -1.0 / (R_hat * a_v);
            // const C_hat_i = -1.0 / (R_hat * a_i);
            // const C_hat = (C_hat_v + C_hat_i) / 2.0;

            results.data["E"].push(E);
            results.data["R"].push(R);
            results.data["C"].push(C);
            results.data["sigma_v"].push(source.data["sigma_v"][0]);
            results.data["sigma_i"].push(source.data["sigma_i"][0]);
            results.data["T"].push(T);
            results.data["N"].push(N);
            results.data["T*"].push(T_hat);
            results.data["N*"].push(N_hat);
            results.data["E'"].push(E_hat);
            results.data["R'"].push(R_hat);
            results.data["C'"].push(C_hat);

            // データ更新
            results.change.emit();
        """
    )


def create_download_results_callback(results):
    """ ダウンロードボタンのコールバック """
    return CustomJS(
        args=dict(results=results),
        code="""
            // SheetJSをCDNからロード
            var script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
            script.onload = function() {
                // 最新のデータを取得
                const data = results.data;
                const E = data["E"];
                const R = data["R"];
                const C = data["C"];
                const sigma_v = data["sigma_v"];
                const sigma_i = data["sigma_i"];
                const T = data["T"];
                const N = data["N"];
                const T_hat = data["T*"];
                const N_hat = data["N*"];
                const E_hat = data["E'"];
                const R_hat = data["R'"];
                const C_hat = data["C'"];

                // データを2次元配列に変換（Excelに対応）
                const rows = [
                    ['電源電圧（真値） E [V]', '抵抗値（真値） R [Ω]', '静電容量（真値） C [F]', '電圧計測ノイズ強度 sigma_v', '電流計測ノイズ強度 sigma_i',
                     '周期 T [秒]', '計測数 N [回]', '推定に使用したデータの最終時間 T* [秒]', '推定に使用したデータ数 N* [個]',
                     '電源電圧（推定値） E [V]', '抵抗値（推定値） R [Ω]', '静電容量（推定値） C [F]']
                ];
                for (let n = 0; n < E.length; n++) {
                    rows.push([
                        E[n], R[n], C[n], sigma_v[n], sigma_i[n],
                        T[n], N[n], T_hat[n], N_hat[n],
                        E_hat[n], R_hat[n], C_hat[n]]
                    );
                }

                // xlsxファイルの作成
                var ws = XLSX.utils.aoa_to_sheet(rows);  // 2次元配列からシートを作成
                var wb = XLSX.utils.book_new();  // 新しいワークブック作成
                XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');  // ワークブックにシートを追加

                // ファイル名の設定
                const fileName = 'analysis_result_summary.xlsx';

                // xlsxファイルをダウンロード
                XLSX.writeFile(wb, fileName);  // xlsxファイルをダウンロード
            };
            document.head.appendChild(script);  // スクリプトをHTMLに追加
        """
    )