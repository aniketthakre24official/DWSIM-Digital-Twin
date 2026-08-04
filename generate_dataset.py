"""
generate_dataset.py

Sweeps feed temperature across a DWSIM flash separator flowsheet and logs
the resulting heater duty and phase flow rates to a CSV. This CSV is the
training data consumed by ai_model.py.

Run order: this script FIRST, then ai_model.py.

Usage:
    python generate_dataset.py
    python generate_dataset.py --dwsim-path "C:\\path\\to\\DWSIM" --flowsheet "D:\\models\\Flash_Model.dwxmz"

Or configure once via environment variables (handy for CI / other machines):
    set DWSIM_PATH=C:\\path\\to\\DWSIM
    set DWSIM_FLOWSHEET=D:\\models\\Flash_Model.dwxmz
    python generate_dataset.py

Requires a local DWSIM installation (Windows, .NET) — see README.md.
"""

import argparse
import os
import sys

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a feed-temperature sweep dataset from a DWSIM flowsheet."
    )
    parser.add_argument(
        "--dwsim-path",
        default=os.environ.get("DWSIM_PATH", r"C:\Users\Public\DWSIM"),
        help="Path to your local DWSIM install directory (contains DWSIM.Automation.dll). "
        "Defaults to $DWSIM_PATH env var if set.",
    )
    parser.add_argument(
        "--flowsheet",
        default=os.environ.get(
            "DWSIM_FLOWSHEET",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "Flash_Model.dwxmz"),
        ),
        help="Path to the .dwxmz flowsheet file to load. "
        "Defaults to $DWSIM_FLOWSHEET env var, or Flash_Model.dwxmz next to this script.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "Flash_Dataset.csv"),
        help="Where to write the generated CSV (default: Flash_Dataset.csv next to this script).",
    )
    parser.add_argument(
        "--temp-start", type=int, default=290, help="Sweep start temperature in K (default: 290)"
    )
    parser.add_argument(
        "--temp-end", type=int, default=372, help="Sweep end temperature in K, exclusive (default: 372)"
    )
    parser.add_argument(
        "--temp-step", type=int, default=2, help="Sweep step size in K (default: 2)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.isdir(args.dwsim_path):
        print(f"DWSIM install path not found: {args.dwsim_path}")
        print("Pass --dwsim-path or set the DWSIM_PATH env var. See README.md.")
        sys.exit(1)
    if not os.path.isfile(args.flowsheet):
        print(f"Flowsheet file not found: {args.flowsheet}")
        print("Pass --flowsheet or set the DWSIM_FLOWSHEET env var. See README.md.")
        sys.exit(1)

    sys.path.append(args.dwsim_path)

    try:
        import clr

        clr.AddReference("DWSIM.Automation")
    except Exception as e:
        print(f"Could not load DWSIM.Automation from {args.dwsim_path}: {e}")
        print("Check that --dwsim-path points at a valid DWSIM install and that you're running "
              "a Windows Python (pythonnet requires .NET).")
        sys.exit(1)

    from DWSIM.Automation import Automation3

    simulator = Automation3()
    print("DWSIM engine started.")

    try:
        sim = simulator.LoadFlowsheet(args.flowsheet)
    except Exception as e:
        print(f"Failed to load flowsheet '{args.flowsheet}': {e}")
        sys.exit(1)
    print(f"Flowsheet loaded: {args.flowsheet}")

    try:
        feed_stream = sim.GetFlowsheetSimulationObject("FEED").GetAsObject()
        vap_out = sim.GetFlowsheetSimulationObject("VAP OUT").GetAsObject()
        liq_out = sim.GetFlowsheetSimulationObject("LIQ OUT").GetAsObject()
        heater_energy = sim.GetFlowsheetSimulationObject("E1").GetAsObject()
    except Exception as e:
        print(f"Could not find one of the expected flowsheet objects "
              f"(FEED / VAP OUT / LIQ OUT / E1): {e}")
        print("Check that the object names in Flash_Model.dwxmz match these tags.")
        sys.exit(1)

    dataset = []
    print("\nStarting AI data-generation sweep...")
    print("-" * 50)

    temps = range(args.temp_start, args.temp_end, args.temp_step)
    for i, temp in enumerate(temps):
        try:
            feed_stream.SetTemperature(float(temp))
            simulator.CalculateFlowsheet2(sim)

            v_flow = vap_out.Mixture.Properties.massflow
            l_flow = liq_out.Mixture.Properties.massflow
            duty_kw = heater_energy.EnergyFlow

            if v_flow is None or l_flow is None or duty_kw is None:
                print(f"[{i+1}/{len(temps)}] Feed {temp} K: solver returned no value "
                      f"(likely non-convergence) — skipping this point.")
                continue

            dataset.append(
                {
                    "Feed_Temperature_K": temp,
                    "Heater_Duty_kW": duty_kw,
                    "Vapor_Flow_kg_s": v_flow,
                    "Liquid_Flow_kg_s": l_flow,
                }
            )
            print(f"[{i+1}/{len(temps)}] Feed: {temp} K | Heater Duty: {duty_kw:.2f} kW | "
                  f"Vapor: {v_flow:.4f} kg/s")

        except Exception as e:
            print(f"[{i+1}/{len(temps)}] Feed {temp} K: calculation failed — {e}")
            continue

    if not dataset:
        print("No data points were generated — check flowsheet convergence and object names.")
        sys.exit(1)

    df = pd.DataFrame(dataset)
    df.to_csv(args.output, index=False)
    print("-" * 50)
    print(f"Success! {len(df)}/{len(temps)} points saved to: {args.output}")
    print("Next: run `python ai_model.py` to train the soft sensor.")


if __name__ == "__main__":
    main()
