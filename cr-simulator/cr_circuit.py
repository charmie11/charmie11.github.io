import numpy as np
import pandas as pd
import plotly.express as px


settings = {
    'V': {'min': 1.0, 'max': 20.0, 'step': 1.0, 'default': 1.0, 'text': '電源電圧 [V]'},
    'R': {'min': 1.0, 'max': 150.0, 'step': 1.0, 'default': 2.0, 'text': '抵抗 [Ohm]'},
    'C': {'min': 1.0, 'max': 30.0, 'step': 1.0, 'default': 3.0, 'text': '静電容量 [F]'},
    'T': {'min': 1.0, 'max': 40000.0, 'step': 1.0, 'default': 50.0, 'text': '周期 [秒]'},
    'N': {'min': 10, 'max': 2000, 'step': 10, 'default': 10, 'text': 'サンプル数 [回/半周期]'},
}


class Circuit:
    def __init__(self, voltage, period, resistance, capacitance):
        self.V = voltage
        self.T = period
        self.R = resistance
        self.C = capacitance
        self.tau = self.R * self.C

    def measure(self, num_samples):
        assert num_samples > 1
        times = np.linspace(0, self.T, 2*num_samples)

        v_charge = self.V * (1.0 - np.exp(-times[:num_samples]/self.tau))
        v_charge[v_charge>self.V] = self.V

        v_offset = self.V - v_charge[-1]
        time_offset = times[num_samples-1]
        v_discharge = self.V * np.exp(-(times[num_samples:]-time_offset)/self.tau) - v_offset
        v_discharge[v_discharge<0.0] = 0.0
        num_data = len(times)

        df = pd.DataFrame({
            '電源電圧 [V]': [self.V] + [None] * (num_data - 1),
            '抵抗 [Ω]': [self.R] + [None] * (num_data - 1),
            '静電容量(真値) [F]': [self.C] + [None] * (num_data - 1),
        })
        df["時間 [秒]"] = times
        df["コンデンサの端子電圧 [V]"] = np.concat([v_charge, v_discharge])

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
                range=[0, 1.1*self.V],
                tickformat='.1f',
            )
        )
        # fig.add_vline(x=0.5*self.T, line_dash="dash")
        fig.add_hline(y=self.V, line_dash="dash")

        return df, fig
