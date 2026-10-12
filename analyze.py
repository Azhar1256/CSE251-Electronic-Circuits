"""Run every CSE251 netlist in ngspice, compute the key measurements and save the plots.

Usage:  python analyze.py          (needs ngspice on PATH, numpy, matplotlib)
"""
import json
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent
CIRCUITS, RESULTS = ROOT / "circuits", ROOT / "results"


def simulate():
    RESULTS.mkdir(exist_ok=True)
    for cir in sorted(CIRCUITS.glob("*.cir")):
        subprocess.run(["ngspice", "-b", cir.name], cwd=CIRCUITS, check=True, capture_output=True)


def load(name, ncols):
    """ngspice `wrdata` writes (x, y) pairs per vector; return x and the y columns."""
    d = np.loadtxt(RESULTS / f"{name}.csv")
    return d[:, 0], [d[:, 2 * k + 1] for k in range(ncols)]


def steady(t, *ys, after=0.04):
    m = t >= after
    return (t[m],) + tuple(y[m] for y in ys)


def analyse():
    out = {}

    # Lab 1a: diode I-V
    _, (vd, id_ma) = load("lab1_diode_iv", 2)                 # columns: sweep, Vd, sweep, Id
    knee = vd[np.argmax(id_ma >= 1.0)]                       # forward voltage at 1 mA
    out["lab1_forward_voltage_at_1mA_V"] = round(float(knee), 3)
    out["lab1_reverse_current_at_-5V_uA"] = round(float(-id_ma[0] * 1000), 4)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(vd, id_ma); ax.axhline(0, lw=.5, c="k"); ax.axvline(0, lw=.5, c="k")
    ax.set(xlabel="Diode voltage (V)", ylabel="Diode current (mA)", title="Lab 1: 1N4148 I-V characteristic", xlim=(-1, 1))
    ax.annotate(f"≈{knee:.2f} V at 1 mA", (knee, 1), (0.1, 3), arrowprops=dict(arrowstyle="->"))
    fig.tight_layout(); fig.savefig(RESULTS / "lab1_diode_iv.png", dpi=150); plt.close(fig)

    # Lab 1b: half-wave rectifier
    t, (vin, vout) = load("lab1_half_wave", 2)
    t, vin, vout = steady(t, vin, vout)
    out["lab1_halfwave_peak_out_V"] = round(float(vout.max()), 3)
    out["lab1_halfwave_drop_V"] = round(float(vin.max() - vout.max()), 3)
    out["lab1_halfwave_dc_out_V"] = round(float(vout.mean()), 3)            # theory ≈ Vp_out/π
    out["lab1_halfwave_dc_theory_V"] = round(float(vout.max() / np.pi), 3)
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(t * 1e3, vin, label="Input"); ax.plot(t * 1e3, vout, label="Output (1 kΩ)")
    ax.set(xlabel="Time (ms)", ylabel="Voltage (V)", title="Lab 1: half-wave rectifier"); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(RESULTS / "lab1_half_wave.png", dpi=150); plt.close(fig)

    # Lab 2: bridge rectifier, unfiltered vs filtered
    fig, ax = plt.subplots(figsize=(7, 3.5))
    for name, label in [("lab2_bridge_unfiltered", "no capacitor"), ("lab2_bridge_filtered", "100 µF capacitor")]:
        t, (vin, vout) = load(name, 2)
        t, vin, vout = steady(t, vin, vout, after=0.06)
        key = "unfiltered" if "un" in name else "filtered"
        out[f"lab2_{key}_peak_V"] = round(float(vout.max()), 3)
        out[f"lab2_{key}_dc_V"] = round(float(vout.mean()), 3)
        out[f"lab2_{key}_ripple_Vpp"] = round(float(vout.max() - vout.min()), 3)
        if key == "unfiltered":
            ax.plot(t * 1e3, vin, c="0.7", lw=1, label="Input")
            out["lab2_bridge_drop_V"] = round(float(vin.max() - vout.max()), 3)    # two diodes conduct
            # output ripple frequency: rising zero-crossings of (vout - mean) per second
            s = np.signbit(vout - vout.mean()).astype(int)
            out["lab2_ripple_frequency_Hz"] = round(float(np.sum(np.diff(s) == -1) / (t[-1] - t[0])))
        ax.plot(t * 1e3, vout, label=f"Output, {label}")
    peak = out["lab2_filtered_peak_V"]
    out["lab2_filtered_ripple_theory_Vpp"] = round(peak / (2 * 50 * 1e3 * 100e-6), 3)   # Vr ≈ Vp / (2 f R C)
    ax.set(xlabel="Time (ms)", ylabel="Voltage (V)", title="Lab 2: full-wave bridge rectifier"); ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(RESULTS / "lab2_full_wave_bridge.png", dpi=150); plt.close(fig)

    # Lab 3: Zener regulator
    vin, (vout,) = load("lab3_line_regulation", 1)
    m = (vin >= 8) & (vin <= 15)
    out["lab3_regulated_V_at_12V_in"] = round(float(np.interp(12, vin, vout)), 3)
    out["lab3_line_regulation_mV_per_V"] = round(float(np.polyfit(vin[m], vout[m], 1)[0] * 1000), 2)
    il, (vl,) = load("lab3_load_regulation", 1)
    out["lab3_load_regulation_pct_0_to_20mA"] = round(float((vl[0] - np.interp(0.02, il, vl)) / np.interp(0.02, il, vl) * 100), 2)
    out["lab3_dropout_load_current_mA"] = round(float(il[np.argmax(vl < 0.95 * vl[0])] * 1000), 1)
    out["lab3_dropout_theory_mA"] = round((12 - 5.1) / 220 * 1000, 1)        # all of Rs current goes to the load
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.5))
    a1.plot(vin, vout); a1.plot(vin, vin, "--", c="0.6", label="Input (no regulation)")
    a1.set(xlabel="Input voltage (V)", ylabel="Output voltage (V)", title="Line regulation (no load)"); a1.legend(fontsize=8)
    a2.plot(il * 1e3, vl); a2.axvline(out["lab3_dropout_theory_mA"], ls=":", c="0.5")
    a2.set(xlabel="Load current (mA)", ylabel="Output voltage (V)", title="Load regulation (12 V input)")
    fig.suptitle("Lab 3: 5.1 V Zener shunt regulator"); fig.tight_layout(); fig.savefig(RESULTS / "lab3_zener_regulator.png", dpi=150); plt.close(fig)

    (RESULTS / "measurements.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


if __name__ == "__main__":
    simulate()
    for k, v in analyse().items():
        print(f"{k:42s} {v}")
