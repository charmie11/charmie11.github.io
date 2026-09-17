import random
from itertools import combinations
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.models import Select, Button, ColumnDataSource, CustomJS, Div
from bokeh.embed import file_html
from bokeh.resources import CDN


def create_groups_config(random_seed=42):
    """
    シミュレーションの前提条件となる全15グループの設定を生成します。
    - アルファベット（A, B, C）で電源電圧 E を決定（5V, 10V, 15V）
    - 6C3 = 20通りからランダムに15通りの組み合わせを抽出して各グループに割り当て
    """
    group_prefixes = ['A', 'B', 'C']
    group_numbers = range(1, 6)
    all_groups = [f"{p}{n}" for p in group_prefixes for n in group_numbers]

    E6_VALUES_uF = [10, 15, 22, 33, 47, 68]
    all_combinations = [list(c) for c in combinations(E6_VALUES_uF, 3)]

    # 乱数シードを固定して20通りから15通りをシャッフル抽出
    rng = random.Random(random_seed)
    selected_combinations = rng.sample(all_combinations, len(all_groups))

    voltage_map = {'A': 5.0, 'B': 10.0, 'C': 15.0}

    groups_config = {}
    for idx, group_name in enumerate(all_groups):
        prefix = group_name[0]
        assigned_caps = selected_combinations[idx]

        groups_config[group_name] = {
            'voltage_E': voltage_map[prefix],
            'nominal_caps_uF': sorted(assigned_caps)
        }

    return groups_config, all_groups


def create_widgets(all_groups):
    """
    シミュレータのUIを構成するBokehウィジェットを生成します。
    """
    widgets = {}
    widgets['source'] = ColumnDataSource(data={'t': [], 'v1': [], 'v2': [], 'v3': []})
    widgets['full_data_source'] = ColumnDataSource(data={'t': [], 'v1': [], 'v2': [], 'v3': []})

    group_title = Div(text="<div style='font-size: 15px; font-weight: bold; margin-bottom: 5px;'>【実験グループの選択】</div>")
    widgets['group_title'] = group_title

    widgets['prefix_select'] = Select(title="アルファベット", value="A", options=['A', 'B', 'C'], width=110)
    widgets['number_select'] = Select(title="数字", value="1", options=[str(i) for i in range(1, 6)], width=110)

    widgets['v0_display'] = Div(
        text="<div style='font-size: 14px; font-weight: 600; color: #1f77b4;'>電源電圧 E: 5.0 V</div>",
        margin=(10, 0, 5, 0)
    )

    initial_r_text = "<div style='font-size: 14px; font-weight: 600;'>抵抗値 R: 100,000 Ω (100 kΩ 固定)</div>"
    widgets['r_label'] = Div(text=initial_r_text, margin=(0, 0, 10, 0))

    widgets['start_button'] = Button(label="計測開始", button_type="success", width=230)
    widgets['download_link'] = Div(
        text="""
        <a id="cr-csv-download"
           style="display:inline-block;width:230px;box-sizing:border-box;
                  text-align:center;padding:8px 10px;border-radius:4px;
                  background:#337ab7;color:#fff;text-decoration:none;
                  pointer-events:none;opacity:0.5;">
          計測データをダウンロード (.csv)
        </a>
        """,
        width=230,
    )

    # 散布図の作成（Googleスプレッドシートのデフォルト系列色：青、赤、オレンジ）
    p = figure(height=400, width=620, title="CR回路 充電電圧のシミュレーション",
               x_axis_label="時刻 t [s]", y_axis_label="コンデンサ端子電圧 V [V]")
    colors = ["#4285f4", "#ea4335", "#ff9900"]  # 青, 赤, オレンジ
    labels = ["コンデンサ 1", "コンデンサ 2", "コンデンサ 3"]

    for i in range(3):
        p.scatter(x='t', y=f'v{i + 1}', source=widgets['source'], marker='circle', size=5,
                  color=colors[i], legend_label=labels[i])

    p.legend.location = "bottom_right"
    p.legend.click_policy = "hide"
    p.legend.title = "凡例"
    widgets['plot'] = p

    return widgets


def create_callbacks(widgets, groups_config):
    """
    ウィジェットの動作を定義するJavaScriptコールバックを作成します。
    """
    prefix_change_js = CustomJS(args=dict(
        prefix_select=widgets['prefix_select'],
        v0_display=widgets['v0_display']
    ), code="""
        const prefix = prefix_select.value;
        const vMap = {'A': '5.0', 'B': '10.0', 'C': '15.0'};
        v0_display.text = `<div style='font-size: 14px; font-weight: 600; color: #1f77b4;'>電源電圧 E: ${vMap[prefix]} V</div>`;
    """)
    widgets['prefix_select'].js_on_change('value', prefix_change_js)

    start_measurement_js = CustomJS(args=dict(
        source=widgets['source'],
        full_data_source=widgets['full_data_source'],
        prefix_select=widgets['prefix_select'],
        number_select=widgets['number_select'],
        start_button=widgets['start_button'],
        plot=widgets['plot'],
        groups_config=groups_config
    ), code="""
        function findDownloadLink() {
            const queue = [document];
            while (queue.length) {
                const root = queue.shift();
                const el = root.getElementById ? root.getElementById('cr-csv-download') : null;
                if (el) { return el; }
                const nodes = root.querySelectorAll ? root.querySelectorAll('*') : [];
                for (const node of nodes) {
                    if (node.shadowRoot) { queue.push(node.shadowRoot); }
                }
            }
            return null;
        }

        function disableDownloadLink() {
            const a = findDownloadLink();
            if (!a) { return; }
            a.style.pointerEvents = 'none';
            a.style.opacity = '0.5';
            a.removeAttribute('href');
        }

        function enableDownloadLink(group, E, data) {
            const t = data['t'];
            if (!t || t.length === 0) { return; }

            const R = 100000;
            const mainHeaders = [
                "電源電圧_E [V]",
                "時刻_t [s]",
                "電圧1 [V]",
                "電圧2 [V]",
                "電圧3 [V]",
                "時刻_t [s]",
                "変換電圧1",
                "変換電圧2",
                "変換電圧3",
                "抵抗値_R [ohm]",
                "傾き1",
                "傾き2",
                "傾き3",
                "計算値1 [μF]",
                "計算値2 [μF]",
                "計算値3 [μF]"
            ];
            const tableBlock = [
                ["公称値候補 [μF]", "差の絶対値（計算値1）", "差の絶対値（計算値2）", "差の絶対値（計算値3）", "推定値1 [μF]", "推定値2 [μF]", "推定値3 [μF]"],
                ["10", "", "", "", "", "", ""],
                ["15", "", "", "", "", "", ""],
                ["22", "", "", "", "", "", ""],
                ["33", "", "", "", "", "", ""],
                ["47", "", "", "", "", "", ""],
                ["68", "", "", "", "", "", ""]
            ];

            let csv_content = "\\uFEFF" + mainHeaders.join(",") + ",," + tableBlock[0].join(",") + "\\n";
            for (let i = 0; i < t.length; i++) {
                let R_str = "";
                if (i == 0) {
                    R_str = R.toFixed(0);
                }
                const row = [
                    E.toFixed(1),
                    t[i].toFixed(4),
                    data['v1'][i].toFixed(4),
                    data['v2'][i].toFixed(4),
                    data['v3'][i].toFixed(4),
                    t[i].toFixed(4),
                    "", "", "",
                    R_str,
                    "", "", "",
                    "", "", ""
                ];
                let tableCols = ["", "", "", "", "", "", ""];
                if (i < 6) {
                    tableCols = tableBlock[i + 1];
                }
                csv_content += row.join(",") + ",," + tableCols.join(",") + "\\n";
            }

            const a = findDownloadLink();
            if (!a) { return; }
            a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(csv_content);
            a.download = "measurement_data_group_" + group + ".csv";
            a.style.pointerEvents = "auto";
            a.style.opacity = "1";
        }

        if (window.animationInterval) { clearInterval(window.animationInterval); }

        disableDownloadLink();
        start_button.disabled = true;
        source.data = {'t': [], 'v1': [], 'v2': [], 'v3': []};
        source.change.emit();

        const prefix = prefix_select.value;
        const number = number_select.value;
        const group = prefix + number;

        const config = groups_config[group];
        const E = config.voltage_E;
        const nominal_caps_uF = config.nominal_caps_uF;
        const R = 100000.0;

        const true_caps_F = nominal_caps_uF.map(c => c * 1e-6);
        const taus = true_caps_F.map(C => R * C);
        const max_tau = Math.max(...taus);
        const t_end = 7.0 * max_tau;
        const num_data_points = 100;
        const t_full = Array.from({length: num_data_points}, (_, i) => i * t_end / (num_data_points - 1));

        const voltages = [[], [], []];
        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < num_data_points; j++) {
                const v_ideal = E * (1.0 - Math.exp(-t_full[j] / taus[i]));
                voltages[i].push(v_ideal);
            }
        }

        full_data_source.data = {
            't': t_full,
            'v1': voltages[0],
            'v2': voltages[1],
            'v3': voltages[2]
        };
        full_data_source.change.emit();

        plot.y_range.start = 0;
        plot.y_range.end = E * 1.05;

        let animation_step = 0;
        const total_steps = 100;
        window.animationInterval = setInterval(() => {
            animation_step++;
            const current_points = Math.floor((animation_step / total_steps) * num_data_points);

            if (current_points >= num_data_points) {
                source.data = full_data_source.data;
                clearInterval(window.animationInterval);
                enableDownloadLink(group, E, full_data_source.data);
                start_button.disabled = false;
            } else {
                source.data = {
                    't': full_data_source.data.t.slice(0, current_points),
                    'v1': full_data_source.data.v1.slice(0, current_points),
                    'v2': full_data_source.data.v2.slice(0, current_points),
                    'v3': full_data_source.data.v3.slice(0, current_points)
                };
            }
            source.change.emit();
        }, 25);
    """)
    widgets['start_button'].js_on_click(start_measurement_js)


def create_layout(widgets):
    """
    UIコンポーネントを配置します。
    """
    group_select_row = row(
        widgets['prefix_select'],
        widgets['number_select'],
        sizing_mode="fixed"
    )

    controls = column(
        widgets['group_title'],
        group_select_row,
        widgets['v0_display'],
        widgets['r_label'],
        widgets['start_button'],
        widgets['download_link'],
        styles={
            'background-color': '#f8f9fa',
            'padding': '15px',
            'border-radius': '6px',
            'border': '1px solid #dee2e6'
        },
        width=260
    )

    layout = row(controls, widgets['plot'], spacing=20)
    return layout


def save_configs(groups_config, path):
    """
    教員用の正解参照・割り当て設定表をCSVに保存します。
    """
    print("\n--- 全15グループの正解・設定一覧（ランダム割り当て） ---")
    csv_output = ["グループ名,電源電圧 [V],公称値1 [uF],公称値2 [uF],公称値3 [uF]\n"]

    for group_name, config in groups_config.items():
        caps = config['nominal_caps_uF']
        E = config['voltage_E']
        print(f"グループ {group_name:<3}: E = {E:>4.1f} V | 公称値 = {str(caps):<15}")
        csv_row = f"{group_name},{E:.1f},{caps[0]},{caps[1]},{caps[2]}\n"
        csv_output.append(csv_row)

    with open(path, 'w', encoding='utf-8-sig') as f:
        f.writelines(csv_output)
    print(f"\n✅ 設定一覧を '{path}' に保存しました。")


def main():
    groups_config, all_groups = create_groups_config(random_seed=42)
    widgets = create_widgets(all_groups)
    create_callbacks(widgets, groups_config)
    layout = create_layout(widgets)

    save_configs(groups_config, "configs.csv")

    html = file_html(layout, CDN, "CR回路シミュレータ")
    with open('app.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ 'app.html' が正常に生成されました。")


if __name__ == "__main__":
    main()