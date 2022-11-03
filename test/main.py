# -*- coding: utf-8 -*-
import os
import numpy as np

from bokeh.models import Paragraph
from bokeh.layouts import column, row, Spacer
from bokeh.models import CustomJS, Slider, RadioButtonGroup, Button, HoverTool
from bokeh.plotting import ColumnDataSource, figure, output_file, show
from bokeh.models import NumeralTickFormatter


def main():
    # parameters
    Vs = [1.0, 10.0]
    # Rs = [1e3, 1e5]
    Rs = [1e4, 1e5]
    Cs = [1e-8, 1e-7]
    Taus = [Rs[0]*Cs[0], Rs[1]*Cs[1]]

    V_0 = np.mean(Vs)
    R_0 = 5e4
    C_0 = 5e-8
    # R_0 = Rs[0]
    # C_0 = Cs[0]
    Tau_0 = C_0 * R_0
    Tau_max = Cs[1] * Rs[1]
    t = np.linspace(-Tau_max, 6*Tau_max, 2000)
    v_c = V_0 * (1.0 - np.exp(-t/Tau_0))
    v_c[np.where(t < 0.0)] = 0.0
    v = V_0 * np.ones(t.shape)
    v[np.where(t < 0)] = 0.0
    i_c = (V_0 - v_c) / R_0
    i_c[np.where(t < 0.0)] = 0.0
    # observation_v = ColumnDataSource(data=dict(t=t, v_c=v_c, v=v))
    observation_v = ColumnDataSource(data=dict(t=t, v_c=v_c))
    observation_i = ColumnDataSource(data=dict(t=t, i_c=i_c))

    """ plot """
    plot_options = dict(plot_width=512, plot_height=300, x_axis_label="Time [s]")

    # plot V
    plot_v = figure(x_range=(-5e-3, 6*Tau_max),
                    y_axis_label="Volt [V]",
                    y_range=(-0.3*Vs[0], 1.1*Vs[1]),
                    **plot_options)
    # plot_v.title.text = "電源電圧とコンデンサの電圧"
    plot_v.title.text = "コンデンサの電圧"
    plot_v.title.align = "center"
    plot_v.title_location = "below"
    plot_v.yaxis[0].formatter = NumeralTickFormatter(format="0.0")

    # line_v = plot_v.circle('t', 'v', source=observation_v, size=1.0, color='blue', legend_label='V')
    line_v_c = plot_v.circle('t', 'v_c', source=observation_v, size=1.0, color='red', legend_label='V_c')
    plot_v.legend.location = 'bottom_right'
    plot_v.legend.click_policy = "hide"
    hover_v = HoverTool(
        renderers=[line_v_c],
        tooltips=[
            ("Time", "@t"),
            ("V_c", "@v_c")
        ],
        mode="vline"
    )
    plot_v.add_tools(hover_v)

    # plot I
    plot_i = figure(x_range=plot_v.x_range,
                    y_axis_label="Current [A]",
                    y_range=(-1.1*Vs[1]/Rs[0], 1.1*Vs[1]/Rs[0]),
                    **plot_options)
    plot_i.title.text = "回路に流れる電流"
    plot_i.title.align = "center"
    plot_i.title_location = "below"
    plot_i.yaxis[0].formatter = NumeralTickFormatter(format="0.0000")

    line_i_c = plot_i.circle('t', 'i_c', source=observation_i, size=1.0, color='green', legend_label='I_c')
    plot_i.legend.location = 'top_right'
    hover_i = HoverTool(
        renderers=[line_i_c],
        tooltips=[
            ("Time", "@t"),
            ("I_c", "@i_c")
        ],
        mode="vline"
    )
    plot_i.add_tools(hover_i)

    """ widgets """
    # sliders
    amplitude = Slider(value=V_0, start=Vs[0], end=Vs[1], step=0.01, title=u"電源電圧 [V]", format="0.00")
    resistance = Slider(value=R_0, start=Rs[0], end=Rs[1], step=100.0, title=u'抵抗値 (内部抵抗含む) [Ω]')
    capacitance = Slider(value=C_0, start=Cs[0], end=Cs[1], step=1e-8, title=u"静電容量 [F]", format="0.00000000")

    # buttons
    mode_charge = RadioButtonGroup(labels=[u"充電", u"放電"], active=0)
    mode_charge.button_type = "success"
    mode_noise = RadioButtonGroup(labels=["ノイズなし", "ノイズあり"], active=0)
    mode_noise.button_type = "success"

    code_sliders = """
        // data from GUI
        var mode_n = mode_noise.active;
        var mode_c = mode_charge.active;
        const V = amp.value;
        //const V = Math.round(10.0*amp.value)/10.0;
        const R = res.value;
        const C = cap.value;
        
        // data of voltage
        var data_v = observation_v.data;
        data_v['t'] = [];
        data_v['v_c'] = [];
//        data_v['v'] = [];
        
        // data of current
        var data_i = observation_i.data;
        data_i['t'] = [];
        data_i['i_c'] = [];
        
        // data of time
        const tau = R * C;
//        const t_step = 0.01 * tau;
//        const t_max = 7.0*tau;
//        const t_step = 0.000001;
//        var t_i = -0.0001;
//        const t_max = 6.0 * 0.01 + t_step;
        const tau_max = 0.01;
        const t_max = 6*tau_max;
        const t_step = 7 * tau_max / 2000;
        var t_i = -tau_max;

        // main loop
        while(t_i < t_max){
            // update t
            data_v['t'].push(t_i);
            data_i['t'].push(t_i);
            
//            // update V
//            if(mode_c == 0){  // Charge
//                data_v['v'].push(t_i < 0.0 ? 0.0 : V);
//            }
//            else{  // Discharge
//                data_v['v'].push(t_i < 0.0 ? V : 0.0);
//            }

            // update V_c
            if(mode_c == 0){  // Charge
                data_v['v_c'].push(Math.max(0.0, V * (1.0 - Math.exp(-t_i/tau))));
            }
            else{  // Discharge
                data_v['v_c'].push(Math.min(V, V * (Math.exp(-t_i/tau))));
            }
            if(mode_n == 1){
                data_v['v_c'][data_v['v_c'].length - 1] += 0.02 * Math.random();
            }
            
            // update I_c
            var V_c = data_v['v_c'][data_v['v_c'].length - 1];
            if(mode_c == 0){  // Charge
                data_i['i_c'].push(t_i < 0.0 ? 0.0 : (V - V_c)/R);
            }
            else{  // Discharge
                data_i['i_c'].push(t_i < 0.0 ? 0.0 : -V_c/R);
            }

            // update t_i
            t_i += t_step;
        }
        observation_v.change.emit();
        observation_i.change.emit();
    """
    callback = CustomJS(args=dict(observation_v=observation_v, observation_i=observation_i,
                                  # time_range=time_range,
                                  amp=amplitude, res=resistance, cap=capacitance,
                                  mode_charge=mode_charge, mode_noise=mode_noise),
                        code=code_sliders)
    for w in [amplitude, resistance, capacitance]:
        w.js_on_change('value', callback)
    for m in [mode_charge, mode_noise]:
        m.js_on_change('active', callback)

    # download button
    button_download = Button(label="ダウンロード", button_type="success")
    callback_download = CustomJS(args=dict(source=observation_v),
                                 code=open(os.path.join(os.path.dirname(__file__), "download.js")).read())
    button_download.js_on_click(callback_download)

    """ layout """
    empty_space = Spacer(height=20)
    title_parameters = Paragraph(text=u"CR回路の各種パラメータ設定用スライダー", align='center')
    par_parameters = Paragraph(text=u"以下のスライダーでパラメータの数値を変更でき，ページ右側のグラフが動的に変化します．")
    parameters = column(title_parameters, par_parameters,
                        amplitude, resistance, capacitance)

    title_modes = Paragraph(text=u"動作変更ボタン", align='center')
    par_modes = Paragraph(text=u"以下のボタンで動作モードを変更でき，ページ右側のグラフが動的に変化します．")
    modes = column(title_modes, par_modes,
                   mode_charge, mode_noise)

    title_download = Paragraph(text=u"波形データダウンロードボタン", align='center')
    par_download = Paragraph(text=u"以下のボタンを押すと，右上のグラフのデータ(時刻，電源電圧，コンデンサの電圧)がcsvファイルとして保存できます．")
    download = column(title_download, par_download, button_download)

    plots = column(plot_v, empty_space, plot_i)

    layout = row(
        column(
            parameters,
            empty_space,
            modes,
            empty_space,
            download
        ),
        plots
    )

    output_file("CR_simulator.html", title="Parameter set with sliders")
    show(layout)


if __name__ == "__main__":
    main()
