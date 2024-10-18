import os

import numpy as np
import pandas as pd

from .cr_circuit import Circuit


class CircuitData:
    def __init__(self, t, V, I):
        for data in [t, V, I]:
            assert isinstance(data, np.ndarray)
        assert len(t) == len(V) == len(I)
        assert len(t) > 1  # need more than 1 for line fitting

        self.t = t
        self.V = V
        self.I = I
        self.N = len(t)

    def estimate_parameters(self, N_use=0):
        """ 時間t, コンデンサの端子電圧V, 回路の電流Iから電源電圧E, 抵抗値R, 静電容量Cを推定
        1. ln_V = ln(V(t))
        2. t-ln_Vの近似直線ln_V = a_v * t + b_vを計算
            a. ln_V_coeffs[0] = b_v
            b. ln_V_coeffs[1] = a_v
            c. ln_V_residuals: 近似直線の残差の二乗和
        3. ln_E = ln_V_coeffs[0]
        4. E = exp(ln_E)
        5. t-ln_Iの近似直線ln_I = a_i * t + b_iを計算
            a. ln_I_coeffs[0] = b_i
            b. ln_I_coeffs[1] = a_i
            c. ln_I_residuals: 近似直線の残差の二乗和
        6. ln_E - ln_R = ln_I_coeffs[0]
        7. ln_R = ln_E - (ln_E - ln_R)
        8. R = exp(ln_R)
        9. 1/(C*R) = -ln_V_coeffs[1]
        10. C*R = -1 / ln_V_coeffs[1]
        11. C = C*R / R
        """
        if N_use < 2:
            N_use = self.N

        t = self.t[:N_use]
        V = self.V[:N_use]
        I = self.I[:N_use]

        # estimate E from valid V
        valid_indices_V = np.where(V > 0)
        ln_V = np.log(V[valid_indices_V])
        ln_V_coeffs, (ln_V_residuals, _, _, _) = np.polynomial.polynomial.polyfit(t[valid_indices_V], ln_V, 1, full=True)
        ln_E = ln_V_coeffs[0]
        estimate_E = np.exp(ln_E)

        # estimate R from valid I and estimate_E
        valid_indices_I = np.where(-I > 0)
        ln_I = np.log(-I[valid_indices_I])
        ln_I_coeffs, (ln_I_residuals, _, _, _) = np.polynomial.polynomial.polyfit(t[valid_indices_I], ln_I, 1, full=True)
        ln_R = ln_E - ln_I_coeffs[0]
        estimate_R = np.exp(ln_R)

        # estimate C from valid V and estimate_R
        tau = -1.0 / ln_V_coeffs[1]
        estimate_C = tau / estimate_R

        return estimate_E, estimate_R, estimate_C


def extract_data_from_excel(filename):
    """ extract data from excel file obtained via CR circuit simulator
    the excel contains the following column
        E, R, C, sigma_v, sigma_i, t, V, "", noisy_V, "", I, "", noisy_I, ""
    """
    assert os.path.exists(filename)
    df = pd.read_excel(filename)
    E = df[df.columns[0]].to_numpy()[0]
    R = df[df.columns[1]].to_numpy()[0]
    C = df[df.columns[2]].to_numpy()[0]
    sigma_v = df[df.columns[3]].to_numpy()[0]
    sigma_i = df[df.columns[4]].to_numpy()[0]
    t = df[df.columns[5]].to_numpy()
    V = df[df.columns[6]].to_numpy()
    noisy_V = df[df.columns[8]].to_numpy()
    I = df[df.columns[10]].to_numpy()
    noisy_I = df[df.columns[12]].to_numpy()
    data_theory = CircuitData(t, V, I)
    data_measured = CircuitData(t, noisy_V, noisy_I)

    return Circuit(E, t[-1], R, C), sigma_v, sigma_i, data_theory, data_measured
