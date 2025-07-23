# 🏭 Finite Capacity Scheduling for a Factory Using Pyomo

This project demonstrates **Finite Capacity Scheduling (FCS)** using the **Pyomo** optimization framework in Python. The goal is to model and solve a factory scheduling problem where machines have limited capacity and must be scheduled efficiently.

---

## 📌 Features

- Models machine capacity constraints
- Supports task precedence and timing
- Gantt chart generation for visualizing schedules
- Pluggable solvers (GLPK, CBC, Gurobi, etc.)

---

## ⚙️ Tech Stack

- Python 3.12+
- [Pyomo](http://www.pyomo.org/)
- [uv](https://github.com/astral-sh/uv) - fast Python package manager
- Optional: `glpk`, `cbc`, or other solvers for backend optimization

---

## 🛠 Installation

> You can run this project on **Linux** or **Windows**. The steps are slightly different depending on your platform.

---

### 🐧 Linux (Ubuntu/Debian)

```bash
# 1. Install uv (if not already installed)
curl -Ls https://astral.sh/uv/install.sh | sh

# 2. Create project environment
uv venv .venv

# 3. Activate environment
source .venv/bin/activate

# 4. Install dependencies
uv pip install -r requirements.txt

# 5. Install solver (e.g., GLPK or CBC)
sudo apt-get update
sudo apt-get install -y glpk-utils coinor-cbc
```

---

### 🪟 Windows (PowerShell)

```powershell
# 1. Install uv using pipx
pip install pipx
pipx install uv

# 2. Create project environment
uv venv .venv

# 3. Activate environment
.venv\Scripts\Activate.ps1

# 4. Install dependencies
uv pip install -r requirements.txt

# 5. Install solver (e.g., GLPK or CBC)
# Download and install from:
# - [GLPK Windows](https://sourceforge.net/projects/winglpk/)
# - [CBC binaries](https://github.com/coin-or/Cbc/releases)
# Add the solver binaries to PATH
```

---

## 📄 Usage

```bash
# Activate the environment
source .venv/bin/activate  # Linux
# OR
.venv\Scripts\Activate.ps1  # Windows

# Run the scheduling model
python fcs_model.py
```

---

## 📊 Output

- Optimization summary in console
- Optional Gantt chart visualization (if enabled)
- Schedules with start/end times per task

---

## 📁 Project Structure

```
├── main.py          # Main Pyomo model
├── requirements.txt      # Dependencies
├── README.md             # Project documentation
└── .venv/                # Virtual environment (not committed)
```

---

## 🔧 Solvers Supported

- GLPK (default)
- CBC
- Gurobi (licensed)
- CPLEX (licensed)

Ensure the solver is installed and accessible in your system PATH.

---

## 🧠 References

- Pyomo documentation: https://pyomo.readthedocs.io
- COIN-OR CBC: https://github.com/coin-or/Cbc


---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Pull requests and improvements are welcome! If you find issues or want to add features like advanced Gantt visualization or multi-resource planning, feel free to contribute.

---

## 👨‍💻 Author

**Rupesh Jadhav**  
Full Stack Blockchain + AI Developer  
rupeshjadhav200211@gmail.com  
