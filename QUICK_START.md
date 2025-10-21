# 🚀 Quick Start Guide - Harbor Stone Retirement Calculator

## Running the App

```bash
cd "/Users/julien/Documents/GitHub/Retirement Calculator"
streamlit run app.py
```

Then open your browser to: **http://localhost:8501**

---

## ✨ Key Features

### 1. **Portfolio Projection**
- Enter your current age, retirement age, and end age
- Set current balance and ongoing contributions
- Configure expected returns, inflation, and fees
- View deterministic timeline projection

### 2. **Liquidity Events** 💰
Click **"Manage Liquidity Events"** in the sidebar to add:
- **One-time events:** House sale, inheritance, major purchase
- **Recurring events:** Rental income, pension, Social Security

Events appear as:
- 🔷 Diamond markers on the chart (one-time events)
- 📋 Legend in bottom-right (recurring events)

### 3. **Monte Carlo Simulation** 🎲
- Enable "Monte Carlo" checkbox in sidebar
- Set number of runs (100-5000)
- View probability of success and percentile bands
- See P10-P90 uncertainty range on chart

### 4. **Scenario Management** 📊
- **Save Scenarios:** Name and save up to 5 scenarios
- **Load Scenarios:** Recall saved configurations
- **Compare Scenarios:** Plot two scenarios side-by-side

### 5. **Professional Charts**
- **Portfolio Balance Chart:** Main projection with event markers
- **Cashflow Chart:** Annual breakdown of contributions, withdrawals, fees, taxes
- **Export:** Download charts as PNG or data as CSV

---

## 🎯 Quick Workflows

### Create a Basic Plan
1. Enter your age and financial info in sidebar
2. Set retirement age and expected returns
3. View projection and terminal balance
4. Save as "Base Case"

### Add House Sale Event
1. Click "Manage Liquidity Events"
2. Add new event: Type = "One-time Inflow"
3. Set age, amount, and tax rate
4. Click "Save Events" and "Back to Dashboard"
5. See diamond marker on chart at sale age

### Run Monte Carlo Analysis
1. Check "Enable Monte Carlo" in sidebar
2. Set runs to 1000
3. View success probability in Key Metrics
4. Expand "Monte Carlo Analysis" to see details
5. Chart shows P10-P90 uncertainty bands

### Compare Two Scenarios
1. Create and save "Conservative" scenario (low returns)
2. Create and save "Aggressive" scenario (high returns)
3. In "Compare Scenarios" section, select both
4. Click "Compare Scenarios"
5. Both lines appear on chart

---

## 🎨 Chart Features

### Portfolio Balance Chart
- **Green line:** Your primary scenario
- **Gold shaded area:** Monte Carlo uncertainty (P10-P90)
- **Vertical dashed line:** Retirement age
- **Diamond markers:** One-time liquidity events
- **Legend box:** Recurring events summary

### Interactive Features
- **Hover:** See detailed values and events at each age
- **Zoom:** Click and drag to zoom
- **Pan:** Shift+drag to pan
- **Reset:** Double-click to reset view

---

## 💡 Pro Tips

### Withdrawal Strategies
- **Fixed % method:** Withdraws percentage of prior year balance (adjusts with portfolio)
- **Fixed real dollars:** Withdraws fixed inflation-adjusted amount (maintains purchasing power)

### Tax Modeling
- Set "Withdrawal Tax Rate" for retirement income
- Set "Tax Rate %" per liquidity event for specific transactions
- Check "Taxable?" for events subject to tax

### Inflation Toggle
- **On:** All future amounts adjusted for inflation (Real vs Nominal view)
- **Off:** No inflation applied (simpler calculation)

---

## 📁 File Locations

```
Retirement Calculator/
├── app.py                    # Main application
├── scenarios.json            # Saved scenarios (auto-created)
├── requirements.txt          # Python dependencies
├── TEST_RESULTS.md          # Test documentation
└── QUICK_START.md           # This guide
```

---

## 🔧 Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Refresh page | `R` |
| Clear cache | `C` |
| Settings menu | `⚙️` (top-right) |

---

## 📊 Understanding the Numbers

### Key Metrics (Top of Page)
- **Terminal Value (Real):** Portfolio value at end age, inflation-adjusted
- **Terminal Value (Nominal):** Actual dollar amount at end age
- **Probability of Success:** % of Monte Carlo runs where portfolio stays positive
- **First Shortfall Age:** Age when portfolio first goes negative (or "None")

### Timeline Columns
- **Start Balance:** Portfolio at beginning of year
- **Contributions:** Annual contributions (stops at retirement)
- **Liquidity Net:** Net from liquidity events this year
- **Withdrawals:** Annual withdrawals (starts at retirement)
- **Fees:** Annual management fees and expenses
- **Taxes:** Taxes from withdrawals and events
- **Growth:** Investment returns for the year
- **End Balance:** Portfolio at end of year

---

## 🆘 Troubleshooting

### App won't start
```bash
# Check Python version (need 3.8+)
python3 --version

# Install dependencies
pip install -r requirements.txt

# Try again
streamlit run app.py
```

### Scenario won't save
- Check you haven't hit the 5-scenario limit
- Try deleting an old scenario first
- Ensure `scenarios.json` is not read-only

### Chart not showing events
- Check events are enabled (toggle on in event editor)
- Verify event ages are within your timeline range
- Ensure amounts are non-zero

### Monte Carlo is slow
- Reduce number of runs (try 500 instead of 5000)
- Shorten timeline (reduce end age)
- Close other applications

---

## 📚 Advanced Features

### Safe Withdrawal Rate Solver
*(Located in detailed analysis section)*
- Automatically finds maximum sustainable withdrawal rate
- Uses binary search algorithm
- Accounts for all your liquidity events and parameters

### Scenario Comparison
- Compare up to 2 scenarios side-by-side
- See differences in terminal values
- Visualize different strategies

### Export Options
- **CSV:** Download full timeline data
- **PNG:** Save chart as high-quality image
- **Scenarios:** Saved automatically to `scenarios.json`

---

## 🎓 Learning Resources

### Understanding Real vs Nominal
- **Nominal:** Actual dollars (e.g., $100 in 2050)
- **Real:** Inflation-adjusted purchasing power (e.g., what $100 in 2050 can buy in today's dollars)
- Toggle in sidebar to switch views

### Monte Carlo Explained
- Runs thousands of simulations with random returns
- Each simulation uses different return sequence
- Shows range of possible outcomes
- Success = portfolio never goes negative

### Liquidity Events Best Practices
1. Start with major known events (house sale, inheritance)
2. Add recurring income (Social Security, pension)
3. Include one-time expenses (new car, medical)
4. Set realistic tax rates per event
5. Review and adjust regularly

---

## ✅ Checklist for New Users

- [ ] Enter basic info (age, balance, retirement age)
- [ ] Set market assumptions (returns, inflation, fees)
- [ ] Configure withdrawal strategy
- [ ] Add major liquidity events
- [ ] Run baseline scenario
- [ ] Save as "Base Case"
- [ ] Enable Monte Carlo to see uncertainty
- [ ] Create alternative scenarios
- [ ] Compare scenarios
- [ ] Export results

---

**Need Help?** Review the help tooltips (ℹ️) next to each input in the sidebar.

**Pro Tip:** Save multiple scenarios to explore different retirement strategies!
