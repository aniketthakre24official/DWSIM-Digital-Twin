import os
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

print("Loading dataset...")
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, "Flash_Dataset.csv")

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"❌ Dataset not found at {csv_path}. Please run testconnection.py first.")
    exit(1)

X = df[['Feed_Temperature_K']] 
y = df['Heater_Duty_kW']

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training AI models (Linear Regression vs Random Forest)...")

# Train Linear Regression
lr_model = LinearRegression()
lr_model.fit(X_train, y_train)
lr_preds = lr_model.predict(X_test)
lr_r2 = r2_score(y_test, lr_preds)

# Train Random Forest
rf_model = RandomForestRegressor(random_state=42)
rf_model.fit(X_train, y_train)
rf_preds = rf_model.predict(X_test)
rf_r2 = r2_score(y_test, rf_preds)

print(f"Linear Regression R² Score: {lr_r2:.4f}")
print(f"Random Forest R² Score: {rf_r2:.4f}")

# Select the best model
if rf_r2 > lr_r2:
    best_model = rf_model
    best_name = "Random Forest"
    best_preds = rf_preds
else:
    best_model = lr_model
    best_name = "Linear Regression"
    best_preds = lr_preds

print(f"✅ Selected Best Model: {best_name}")

# Save the best model
model_path = os.path.join(current_dir, "best_model.joblib")
joblib.dump(best_model, model_path)
print(f"Model saved to {model_path}")

# Generate Parity Plot
plt.figure(figsize=(8, 6))
plt.scatter(y_test, best_preds, color='blue', alpha=0.7, label='Predictions')
plt.plot([y.min(), y.max()], [y.min(), y.max()], 'r--', label='Perfect Prediction')
plt.title(f'Parity Plot: Actual vs Predicted Heater Duty\n({best_name})')
plt.xlabel('Actual Heater Duty (kW)')
plt.ylabel('Predicted Heater Duty (kW)')
plt.legend()
plt.grid(True)
plot_path = os.path.join(current_dir, "parity_plot.png")
plt.savefig(plot_path)
print(f"Parity plot saved to {plot_path}")

# Soft Sensor Test
test_temperature = 325
test_data = pd.DataFrame({'Feed_Temperature_K': [test_temperature]})
predicted_duty = best_model.predict(test_data)

print("-" * 50)
print(f"VIRTUAL SOFT SENSOR PREDICTION:")
print(f"If the incoming feed spikes to {test_temperature} K...")
print(f"The {best_name} AI predicts the Heater Duty will adjust to: {predicted_duty[0]:.2f} kW")
print("-" * 50)
