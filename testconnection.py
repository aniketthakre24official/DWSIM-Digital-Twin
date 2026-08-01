import sys
import os
import argparse
import clr
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="DWSIM Data Generation Loop")
    parser.add_argument("--dwsim-path", type=str, 
                        default=os.environ.get("DWSIM_PATH", r"C:\Users\anike\AppData\Local\DWSIM"),
                        help="Path to DWSIM installation folder")
    parser.add_argument("--flowsheet", type=str, default="Flash_Model.dwxmz",
                        help="Path to the DWSIM flowsheet (.dwxmz)")
    parser.add_argument("--output", type=str, default="Flash_Dataset.csv",
                        help="Path to save the generated dataset")
    
    args = parser.parse_args()

    # 1. Initialize Simulator Engine
    try:
        sys.path.append(args.dwsim_path)
        clr.AddReference("DWSIM.Automation")
        from DWSIM.Automation import Automation3
        simulator = Automation3()
        print("✅ DWSIM Engine started successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize DWSIM engine. Please check your --dwsim-path. Error: {e}")
        return

    # 2. Load Flowsheet
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Use absolute path if provided in CLI, otherwise assume it's in the current directory
        model_path = os.path.join(current_dir, args.flowsheet) if not os.path.isabs(args.flowsheet) else args.flowsheet
        sim = simulator.LoadFlowsheet(model_path)
        print(f"✅ Flowsheet '{args.flowsheet}' loaded successfully.")
    except Exception as e:
        print(f"❌ Failed to load flowsheet. Error: {e}")
        return

    # 3. Target Specific Streams
    try:
        # DWSIM Automation object model requires us to target a flowsheet object by name, 
        # and then call GetAsObject() to interact with its specific properties (like Temperature or MassFlow)
        feed_stream = sim.GetFlowsheetSimulationObject("FEED").GetAsObject()
        vap_out = sim.GetFlowsheetSimulationObject("VAP OUT").GetAsObject()
        liq_out = sim.GetFlowsheetSimulationObject("LIQ OUT").GetAsObject()
        heater_energy = sim.GetFlowsheetSimulationObject("E1").GetAsObject()
    except Exception as e:
        print(f"❌ Failed to target flowsheet objects. Check if names 'FEED', 'VAP OUT', 'LIQ OUT', 'E1' exist. Error: {e}")
        return

    dataset = []
    print("\nStarting the AI Data Generation Loop...")
    print("-" * 50)
    
    try:
        for temp in range(290, 372, 2):
            
            feed_stream.SetTemperature(float(temp))
            simulator.CalculateFlowsheet2(sim)
            
            v_flow = vap_out.Mixture.Properties.massflow
            l_flow = liq_out.Mixture.Properties.massflow
            duty_kw = heater_energy.EnergyFlow 
            
            dataset.append({
                "Feed_Temperature_K": temp,
                "Heater_Duty_kW": duty_kw,
                "Vapor_Flow_kg_s": v_flow,
                "Liquid_Flow_kg_s": l_flow
            })
            
            print(f"Feed: {temp} K | Heater Duty: {duty_kw:.2f} kW | Vapor: {v_flow:.4f} kg/s")
            
        df = pd.DataFrame(dataset)
        out_path = os.path.join(current_dir, args.output) if not os.path.isabs(args.output) else args.output
        df.to_csv(out_path, index=False)
        
        print("-" * 50)
        print(f"✅ Success! Your dynamic AI dataset is saved to: {out_path}")

    except Exception as e:
        print(f"❌ Execution failed during the calculation loop. Error: {e}")

if __name__ == "__main__":
    main()
