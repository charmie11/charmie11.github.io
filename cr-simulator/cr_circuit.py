import numpy as np
import pandas as pd
import plotly.express as px


settings = {
    'E': {'min': 1.0, 'max': 50.0, 'step': 1.0, 'default': 20.0, 'text': '電源電圧 E[V]'},
    'R': {'min': 1.0, 'max': 20.0, 'step': 1.0, 'default': 2.0, 'text': '抵抗 R[Ohm]'},
    'C': {'min': 1.0, 'max': 30.0, 'step': 1.0, 'default': 30.0, 'text': '静電容量 C[F]'},
    'T': {'min': 10.0, 'max': 6000.0, 'step': 10.0, 'default': 300.0, 'text': '半周期 T/2[秒]'},
    'N': {'min': 10, 'max': 1000, 'step': 10, 'default': 100, 'text': 'サンプル数 N[回/半周期]'},
    'voltage_noise': {'min': 0.0, 'max': 2.0, 'step': 0.01, 'default': 0.0, 'text': '電圧計測ノイズ強度'},
    'current_noise': {'min': 0.0, 'max': 0.5, 'step': 0.01, 'default': 0.0, 'text': '電流計測ノイズ強度'},
}


class Circuit:
    def __init__(self, voltage, period, resistance, capacitance):
        self.E = voltage
        self.T = period
        self.R = resistance
        self.C = capacitance
        self.tau = self.R * self.C

    def measure(self, num_samples, mode='charge'):
        assert num_samples > 1
        times = np.linspace(0, self.T, num_samples)
        v_c, i_c = None, None
        if mode == 'charge':
            v_c = self.E * (1.0 - np.exp(-times / self.tau))
            i_c = self.E * np.exp(-times / self.tau) / self.R
        elif mode == 'discharge':
            v_c = self.E * np.exp(-times / self.tau)
            i_c = -self.E * np.exp(-times / self.tau) / self.R
            pass
        else:
            ValueError("mode should be either 'charge' or 'discharge'")

        num_data = len(times)

        df = pd.DataFrame({
            '電源電圧 [V]': [self.E] + [None] * (num_data - 1),
            '抵抗 [Ω]': [self.R] + [None] * (num_data - 1),
            '静電容量(真値) [F]': [self.C] + [None] * (num_data - 1),
        })
        df["時間 [秒]"] = times
        df["コンデンサの端子電圧 [V]"] = v_c
        df["電流 [A]"] = i_c

        return df

    def measure_and_draw(self, num_samples):
        assert num_samples > 1
        df = self.measure(num_samples)

        fig = px.scatter(
            df, x="時間 [秒]", y="コンデンサの端子電圧 [V]",
        )

        fig.update_layout(
            xaxis=dict(
                title="時間 [秒]",
                range=[0, self.T],
                tickformat='.1f',
            ),
            yaxis=dict(
                title="コンデンサの端子電圧 [V]",
                range=[0, 1.1*self.E],
                tickformat='.1f',
            )
        )
        # fig.add_vline(x=0.5*self.T, line_dash="dash")
        fig.add_hline(y=self.E, line_dash="dash")

        return df, fig
