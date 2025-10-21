# Harbor Stone Retirement Calculator

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)

**A professional retirement planning and analysis platform**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Documentation](#documentation)

</div>

---

## 🎯 Overview

Harbor Stone Retirement Calculator is a comprehensive, professional-grade financial planning tool that helps you model and analyze retirement scenarios with precision. Built with a focus on accuracy, flexibility, and user experience, it provides deterministic projections and Monte Carlo simulations to give you confidence in your retirement planning.

### Why Harbor Stone?

- **Professional Grade**: Built with institutional-quality calculations and methodology
- **Flexible Modeling**: Handle complex scenarios with liquidity events, variable contributions, and custom tax rates
- **Probabilistic Analysis**: Monte Carlo simulation shows range of possible outcomes
- **Scenario Comparison**: Evaluate multiple strategies side-by-side
- **Beautiful Visualizations**: Interactive charts with professional Harbor Stone branding
- **Export Ready**: Download data (CSV) and charts (PNG) for reports

---

## ✨ Features

### Core Capabilities

- **📊 Portfolio Projections**
  - Deterministic timeline modeling
  - Real vs. Nominal value toggle
  - Inflation-adjusted calculations
  - Configurable fees and expenses

- **💰 Liquidity Events Management**
  - One-time events (house sale, inheritance, major purchases)
  - Recurring events (rental income, pension, Social Security)
  - Per-event tax modeling
  - Visual indicators on charts

- **🎲 Monte Carlo Simulation**
  - Configurable number of runs (100-5000)
  - Fixed seed for reproducibility
  - Probability of success calculations
  - Percentile bands (P10, P50, P90)

- **📈 Advanced Analytics**
  - Safe withdrawal rate solver
  - Annual cashflow breakdown
  - First shortfall age detection
  - Terminal value analysis

- **💼 Scenario Management**
  - Save up to 5 scenarios
  - Load and modify saved plans
  - Compare scenarios side-by-side
  - Persistent storage (JSON)

- **🎨 Professional UI**
  - Harbor Stone branding (inspired by luxury timepiece aesthetics)
  - Interactive Plotly charts
  - Contextual help tooltips
  - Responsive sidebar controls

---

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/retirement-calculator.git
   cd retirement-calculator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Open in browser**
   - Navigate to `http://localhost:8501`

### Dependencies

```
streamlit>=1.28.0
plotly>=5.17.0
pandas>=2.0.0
numpy>=1.24.0
```

See `requirements.txt` for complete list.

---

## 📖 Usage

### Basic Workflow

1. **Configure Your Profile**
   - Enter current age, retirement age, and planning horizon
   - Set current portfolio balance
   - Define contribution amounts and frequency

2. **Set Market Assumptions**
   - Expected nominal return (%)
   - Return volatility (standard deviation)
   - Inflation rate
   - Annual fees and expenses

3. **Configure Withdrawals**
   - Choose strategy: Fixed % or Fixed real dollars
   - Set withdrawal rate or amount
   - Configure frequency (Annual/Monthly)

4. **Add Liquidity Events**
   - Click "Manage Liquidity Events" in sidebar
   - Add one-time events (house sale, etc.)
   - Add recurring events (pension, etc.)
   - Set tax rates per event

5. **Run Analysis**
   - View deterministic projection
   - Enable Monte Carlo for probabilistic analysis
   - Review key metrics at top of page
   - Export results as needed

6. **Save & Compare**
   - Save scenario for future reference
   - Create alternative scenarios
   - Compare scenarios side-by-side

### Example Scenarios

#### Conservative Retirement Plan
```
Age: 30 → 65 → 95
Balance: $100,000
Contributions: $500/month
Expected Return: 6%
Inflation: 3%
Withdrawal: 4% of balance
```

#### Aggressive Early Retirement
```
Age: 35 → 50 → 85
Balance: $500,000
Contributions: $3,000/month
Expected Return: 8%
Inflation: 3%
Withdrawal: $60,000/year (real)
```

---

## 📊 Key Concepts

### Real vs. Nominal Values

- **Nominal**: Actual dollar amounts (e.g., $100 in 2050)
- **Real**: Inflation-adjusted purchasing power (what those dollars can buy in today's terms)
- Toggle between views in the sidebar

### Monte Carlo Simulation

Runs thousands of scenarios with randomized returns to show:
- Probability of success (portfolio stays positive)
- Range of outcomes (P10-P90 percentile bands)
- Median expected value
- Worst-case and best-case scenarios

### Liquidity Events

Model cash flows beyond regular contributions/withdrawals:
- **One-time**: House sale, inheritance, large expense
- **Recurring**: Rental income, pension, annuity
- Each event can have custom tax treatment

### Withdrawal Strategies

1. **Fixed % of Balance**: Withdraws percentage of prior year's ending balance
   - Adjusts with portfolio performance
   - Never depletes portfolio completely
   - Variable annual income

2. **Fixed Real Dollars**: Withdraws fixed inflation-adjusted amount
   - Maintains purchasing power
   - Predictable income stream
   - Can deplete portfolio if insufficient

---

## 🎨 Screenshots

### Main Dashboard
View portfolio projection with key metrics at top, interactive chart, and comprehensive controls.

### Liquidity Events Manager
Add and manage one-time and recurring cash flows with full tax modeling.

### Monte Carlo Analysis
See probability distributions and uncertainty ranges for your retirement plan.

### Scenario Comparison
Compare multiple strategies side-by-side to find the optimal approach.

---

## 🏗️ Technical Architecture

### Stack
- **Frontend/UI**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Data Structure**: Python dataclasses
- **Storage**: JSON file persistence

### Key Components

```
app.py                      # Main application
├── Dataclasses
│   ├── LiquidityEvent     # Cash flow events
│   ├── TimelineRow        # Annual projection data
│   └── Scenario           # Complete scenario config
├── Core Functions
│   ├── build_timeline()   # Deterministic projection
│   ├── run_monte_carlo()  # Probabilistic simulation
│   ├── apply_liquidity_events()  # Event processing
│   └── solve_safe_withdrawal_rate()  # Optimization
├── UI Components
│   ├── show_liquidity_events_page()  # Event editor
│   ├── create_chart()     # Portfolio visualization
│   └── main()             # Dashboard layout
└── Utilities
    ├── save_scenarios()   # Persistence
    ├── export_csv()       # Data export
    └── export_chart_png() # Chart export
```

### Calculation Methodology

**Timeline Projection (per year):**
```
1. Start Balance
2. + Contributions (pre-retirement)
3. + Liquidity Events (net)
4. - Withdrawals (post-retirement)
5. - Fees (% of balance)
6. - Taxes (on withdrawals and taxable events)
7. × Growth (nominal return)
8. = End Balance
```

**Monte Carlo:**
- Generates random returns: `Return ~ Normal(μ, σ)`
- Runs same timeline calculation with varied returns
- Records outcomes and calculates statistics

---

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - User guide with workflows and tips
- **[TEST_RESULTS.md](TEST_RESULTS.md)** - Comprehensive test report
- **Code Comments** - Extensive docstrings throughout codebase

---

## 🔧 Configuration

### Constants (in `app.py`)

```python
# Default Values
CURRENT_AGE = 30
RETIREMENT_AGE = 65
END_AGE = 95
CURRENT_BALANCE = 100000
CONTRIB_AMOUNT = 500
NOMINAL_RETURN_PCT = 7.0
INFLATION_PCT = 3.0
FEE_PCT = 0.5
WITHDRAWAL_PCT = 4.0

# Monte Carlo
MC_RUNS = 1000
MC_SEED = 42

# Branding
BRAND_PRIMARY = "#003d29"      # Deep forest green
BRAND_SECONDARY = "#c9a961"    # Champagne gold
```

Modify these values to change defaults for your use case.

---

## 🧪 Testing

### Run Tests
```bash
# Syntax check
python3 -m py_compile app.py

# Run application (manual testing)
streamlit run app.py
```

### Test Coverage
- ✅ Timeline calculation accuracy
- ✅ Liquidity events integration
- ✅ Monte Carlo simulation
- ✅ Scenario persistence
- ✅ Chart rendering
- ✅ Export functionality
- ✅ Edge cases (zero values, extreme inputs)

See **[TEST_RESULTS.md](TEST_RESULTS.md)** for detailed test report.

---

## 🗺️ Roadmap

### V1.0 (Current) ✅
- [x] Core timeline projections
- [x] Liquidity events
- [x] Monte Carlo simulation
- [x] Scenario management
- [x] Professional UI/UX
- [x] Export capabilities

### Future Enhancements (V1.1+)
- [ ] Additional chart types (waterfall, pie charts)
- [ ] CSV import for bulk data
- [ ] More tax jurisdictions
- [ ] Retirement account types (401k, IRA, Roth)
- [ ] Asset allocation modeling
- [ ] Healthcare cost projections
- [ ] Social Security integration (US)
- [ ] Multi-currency support
- [ ] Mobile-responsive design
- [ ] PDF report generation

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Add docstrings to all functions
- Keep functions focused and testable

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Streamlit** - For the excellent web framework
- **Plotly** - For beautiful, interactive charts
- **pandas/NumPy** - For data processing capabilities

---

## 📞 Support

- **Documentation**: See [QUICK_START.md](QUICK_START.md)
- **Issues**: Report bugs via GitHub Issues
- **Questions**: Open a Discussion on GitHub

---

## 🔒 Disclaimer

**Important:** This tool is for educational and planning purposes only. It is not financial advice. Always consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results. Retirement planning involves risks, and actual results may differ significantly from projections.

---

## 📊 Project Status

**Current Version:** 1.0.0 (Stable)  
**Last Updated:** October 21, 2025  
**Status:** Production Ready ✅

---

<div align="center">

**Built with ❤️ for better retirement planning**

[⭐ Star this repo](https://github.com/yourusername/retirement-calculator) if you find it helpful!

</div>
