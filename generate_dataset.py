"""
generate_dataset.py

Sweeps feed temperature, pressure, AND mass flow rate across a DWSIM flash
separator flowsheet and logs the resulting heater duty and phase flow rates
to a CSV. This CSV is the training data consumed by ai_model.py.

Run order: this script FIRST, then ai_model.py.

Usage:
    python generate_dataset.py
    python generate_dataset.py --dwsim-path "C:\\path\\to\\DWSIM" --flowsheet "D:\\models\\Flash_Model.dwxmz"

Or configure once via environment variables (handy for CI / other machines):
    set DWSIM_PATH=C:\\path\\to\\DWSIM
    set DWSIM_FLOWSHEET=D:\\models\\Flash_Model.dwxmz
    python generate_dataset.py

NOTE ON RUNTIME: this now sweeps 3 variables instead of 1, so the number of
simulation runs multiplies fast (temp_points x pressure_points x flow_points).
Default ranges below are kept small (5 points each for pressure/flow) to keep
total runtime reasonable -- adjust via the CLI flags if needed.

Requires a local DWSIM installation (Windows, .NET) — see README.md.
"""

import argparse
import itertools
import os
import sys

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a feed temperature/pressure/flow sweep dataset from a DWSIM flowsheet."
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
    parser.add_argument(
        "--pressure-min", type=float, default=1.0, help="Minimum feed pressure in atm (default: 1.0)"
    )
    parser.add_argument(
        "--pressure-max", type=float, default=3.0, help="Maximum feed pressure in atm (default: 3.0)"
    )
    parser.add_argument(
        "--pressure-points", type=int, default=5,
        help="Number of pressure values to sweep between min and max (default: 5)",
    )
    parser.add_argument(
        "--flow-min", type=float, default=1.0, help="Minimum feed mass flow in kg/s (default: 1.0)"
    )
    parser.add_argument(
        "--flow-max", type=float, default=5.0, help="Maximum feed mass flow in kg/s (default: 5.0)"
    )
    parser.add_argument(
        "--flow-points", type=int, default=5,
        help="Number of mass flow values to sweep between min and max (default: 5)",
    )
    return parser.parse_args()


def linspace(start, stop, num):
    """Simple linspace without needing numpy -- num evenly spaced points from start to stop, inclusive."""
    if num == 1:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + i * step for i in range(num)]


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

    temps = list(range(args.temp_start, args.temp_end, args.temp_step))
    pressures = linspace(args.pressure_min, args.pressure_max, args.pressure_points)
    flows = linspace(args.flow_min, args.flow_max, args.flow_points)

    combinations = list(itertools.product(temps, pressures, flows))
    print(f"\nSweeping {len(temps)} temperatures x {len(pressures)} pressures x "
          f"{len(flows)} flows = {len(combinations)} total combinations.")
    print("This will take longer than the original temperature-only sweep.\n")

    dataset = []
    print("Starting AI data-generation sweep...")
    print("-" * 50)

    for i, (temp, pressure_atm, mass_flow) in enumerate(combinations):
        try:
            feed_stream.SetTemperature(float(temp))
            feed_stream.SetPressure(float(pressure_atm) * 101325.0)  # atm -> Pa
            feed_stream.SetMassFlow(float(mass_flow))
            simulator.CalculateFlowsheet2(sim)

            v_flow = vap_out.Mixture.Properties.massflow
            l_flow = liq_out.Mixture.Properties.massflow
            duty_kw = heater_energy.EnergyFlow

            if v_flow is None or l_flow is None or duty_kw is None:
                print(f"[{i+1}/{len(combinations)}] Feed {temp} K, {pressure_atm:.2f} atm, "
                      f"{mass_flow:.2f} kg/s: solver returned no value "
                      f"(likely non-convergence) — skipping this point.")
                continue

            dataset.append(
                {
                    "Feed_Temperature_K": temp,
                    "Feed_Pressure_atm": pressure_atm,
                    "Feed_MassFlow_kg_s": mass_flow,
                    "Heater_Duty_kW": duty_kw,
                    "Vapor_Flow_kg_s": v_flow,
                    "Liquid_Flow_kg_s": l_flow,
                }
            )
            if (i + 1) % 10 == 0 or (i + 1) == len(combinations):
                print(f"[{i+1}/{len(combinations)}] Feed: {temp} K, {pressure_atm:.2f} atm, "
                      f"{mass_flow:.2f} kg/s | Heater Duty: {duty_kw:.2f} kW | "
                      f"Vapor: {v_flow:.4f} kg/s")

        except Exception as e:
            print(f"[{i+1}/{len(combinations)}] Feed {temp} K, {pressure_atm:.2f} atm, "
                  f"{mass_flow:.2f} kg/s: calculation failed — {e}")
            continue

    if not dataset:
        print("No data points were generated — check flowsheet convergence and object names.")
        sys.exit(1)

    df = pd.DataFrame(dataset)
    df.to_csv(args.output, index=False)
    print("-" * 50)
    print(f"Success! {len(df)}/{len(combinations)} points saved to: {args.output}")
    print("Next: run `python ai_model.py` to train the soft sensor.")


if __name__ == "__main__":
    main()
