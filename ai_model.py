import pandas as pd
from sklearn.linear_model import LinearRegression

print("Loading dataset...")
# 1. Load the synthetic data you just generated
df = pd.read_csv(r"D:\DWSIM\Flash_Dataset.csv")

# 2. Define our Features (Input) and Target (Output)
# X must be a 2D array (a dataframe), y is a 1D series
X = df[['Feed_Temperature_K']] 
y = df['Heater_Duty_kW']

print("Training the AI model...")
# 3. Initialize and train the Machine Learning model
# This is where the algorithm studies your 40 data points to find the pattern
model = LinearRegression()
model.fit(X, y)
print("Model training complete!\n")

# 4. The Soft Sensor Test
# Let's ask the AI to predict the duty for a temperature that was NOT in your loop (e.g., 325 K)
test_temperature = 325

# We pass the test temperature to the trained model
predicted_duty = model.predict([[test_temperature]])

print("-" * 50)
print(f"VIRTUAL SOFT SENSOR PREDICTION:")
print(f"If the incoming feed spikes to {test_temperature} K...")
print(f"The AI predicts the Heater Duty will adjust to: {predicted_duty[0]:.2f} kW")
print("-" * 50)