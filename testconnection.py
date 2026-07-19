import clr
import sys
import pandas as pd

# 1. Point to your DWSIM installation
dwsim_path = r"C:\Users\anike\AppData\Local\DWSIM" 
sys.path.append(dwsim_path)

try:
    # 2. Initialize the simulator engine
    clr.AddReference("DWSIM.Automation")
    from DWSIM.Automation import Automation3
    simulator = Automation3()
    print("DWSIM Engine started in the background.")
    
    # 3. Load your Flash Model
    sim = simulator.LoadFlowsheet(r"D:\DWSIM\Flash_Model.dwxmz")
    print("Flowsheet loaded successfully.")
    
    # 4. Target the specific streams
    feed_stream = sim.GetFlowsheetSimulationObject("FEED").GetAsObject()
    vap_out = sim.GetFlowsheetSimulationObject("VAP OUT").GetAsObject()
    liq_out = sim.GetFlowsheetSimulationObject("LIQ OUT").GetAsObject()
    
    # NEW LINE 1: Target the Energy Stream (named E1 on your canvas)
    heater_energy = sim.GetFlowsheetSimulationObject("E1").GetAsObject()
    
    dataset = []
    
    print("\nStarting the AI Data Generation Loop...")
    print("-" * 50)
    
    for temp in range(290, 372, 2):
        
        feed_stream.SetTemperature(float(temp))
        simulator.CalculateFlowsheet2(sim)
        
        v_flow = vap_out.Mixture.Properties.massflow
        l_flow = liq_out.Mixture.Properties.massflow
        
        # NEW LINE 2: Extract the Heater Duty (EnergyFlow is read in kW)
        duty_kw = heater_energy.EnergyFlow 
        
        dataset.append({
            "Feed_Temperature_K": temp,
            "Heater_Duty_kW": duty_kw,       # NEW LINE 3: Save it to the dataset
            "Vapor_Flow_kg_s": v_flow,
            "Liquid_Flow_kg_s": l_flow
        })
        
        # Updated print statement to show the changing duty
        print(f"Feed: {temp} K | Heater Duty: {duty_kw:.2f} kW | Vapor: {v_flow:.4f} kg/s")
        
    df = pd.DataFrame(dataset)
    csv_path = r"D:\DWSIM\Flash_Dataset.csv"
    df.to_csv(csv_path, index=False)
    
    print("-" * 50)
    print(f"Success! Your dynamic AI dataset is saved to: {csv_path}")

except Exception as e:
    print(f"Execution failed: {e}")