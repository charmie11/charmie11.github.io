import os
import glob

from src.ccs.analysis import extract_data_from_excel


def main():
    """ メイン関数 """

    print(os.path.abspath(os.curdir))
    data_dir = "../data"
    filenames = glob.glob(os.path.join(data_dir, "discharge_data*.xlsx"))
    for filename in filenames:
        print(filename)
        circuit, sigma_v, sigma_i, data_theory, data_measured = extract_data_from_excel(filename)
        print(f'  (sigma_v, sigma_i) = ({sigma_v}, {sigma_i})')
        print(f"                真値 (E , R , C ) = {circuit.E}, {circuit.R}, {circuit.C}")
        E_theory, R_theory, C_theory = data_theory.estimate_parameters()
        print(f"  理論値を解析した推定値(E , R , C ) = {E_theory}, {R_theory}, {C_theory}")

        print(f"  計測値を解析した推定値(E , R , C)")
        for N_percent in [10, 30, 50, 100]:
            N_use = int(0.01 * N_percent * data_measured.N)
            E_measured, R_measured, C_measured = data_measured.estimate_parameters(N_use)
            print(f"            {N_use}/{data_measured.N}個の計測値を解析 = {E_measured}, {R_measured}, {C_measured}")


if __name__ == "__main__":
    main()
