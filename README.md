# Industrial AI Soft Sensor: DWSIM Digital Twin

## Project Overview
This repository demonstrates a closed-loop architecture that bridges first-principles chemical simulation with machine learning. Designed as a proof-of-concept for hybrid modeling, it automates a steady-state Vapor-Liquid Flash Separator to generate synthetic plant data, which is then used to train a predictive AI Soft Sensor.

## Architecture & Workflow
1. **The Digital Twin (DWSIM):** A thermodynamic model of a benzene/toluene flash drum, utilizing the Peng-Robinson equation of state to solve the heat and material balances.
2. **The Automation Pipeline (Python):** A custom script acting as a virtual DCS. It programmatically overrides simulator boundary conditions (feed temperatures), commands the solver, and extracts the resulting energy duties to generate a synthetic dataset using `pandas`.
3. **The Predictive AI (Scikit-Learn):** A machine learning algorithm trained on the synthetic dataset to predict required heater duties instantly, bypassing the need for thermodynamic recalculation.

## Engineering Value Proposition
While commercial OTS platforms (such as UniSim Design) are standard for building high-fidelity dynamic models for operator training, this project highlights the transition toward **Industrial AI and Data-Driven Control**. By programmatically generating datasets and deploying ML, this architecture mimics the deployment of real-time predictive soft sensors used in Advanced Process Control (APC) environments to optimize energy consumption and predict asset behavior.

## Repository Contents
* `Flash_Model.dwxmz`: The core physical simulation file.
* `testconnection.py`: The data generation and automation loop.
* `Flash_Dataset.csv`: The synthetic thermodynamic data extracted from the simulator.
* `ai_model.py`: The Scikit-Learn script that trains and deploys the predictive model.
