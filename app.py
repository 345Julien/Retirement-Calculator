"""
Gordon Goss Retirement Calculator
Professional retirement planning and analysis platform

Version: 2.1.0
Release Date: October 21, 2025
License: MIT

QUICK START:
  pip install -r requirements.txt
  streamlit run app.py

Features:
- Portfolio projection with time-value analysis
- Liquidity events management (one-time & recurring)
- Monte Carlo simulation with fixed seed
- Scenario comparison and analysis
- Real/Nominal value toggle
- Export to CSV/PNG
- Scenario persistence to JSON

For documentation, see README.md and QUICK_START.md
"""

__version__ = "2.1.0"
__author__ = "Gordon Goss"
__license__ = "MIT"

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Literal, Optional, Dict, Any
import json
from pathlib import Path
import io
import base64

@dataclass
class LiquidityEvent:
    """Represents a liquidity event (one-time or recurring cash flow)."""
    type: str
    label: str
    start_age: int
    end_age: int
    amount: float
    recurrence: str
    enabled: bool = True
    taxable: bool = False
    tax_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LiquidityEvent':
        # Migrate old type format to new Credit/Debit format
        old_type = data.get('type', '')
        if 'inflow' in old_type.lower():
            data['type'] = 'Credit'
        elif 'outflow' in old_type.lower():
            data['type'] = 'Debit'
        # If type is already Credit/Debit, no change needed
        return cls(**data)


@dataclass
class TimelineRow:
    """Single year in projection timeline."""
    age: int
    start_balance_nominal: float
    contributions: float
    liquidity_net: float
    withdrawals: float
    fees: float
    taxes: float
    growth: float
    end_balance_nominal: float
    cpi_index: float
    end_balance_real: float


@dataclass
class Scenario:
    """Complete scenario configuration."""
    name: str
    current_age: int
    retirement_age: int
    end_age: int
    current_balance: float
    contrib_amount: float
    contrib_cadence: str
    nominal_return_pct: float
    return_stdev_pct: float
    inflation_pct: float
    fee_pct: float
    withdrawal_method: str
    withdrawal_pct: float
    withdrawal_real_amount: float
    withdrawal_frequency: str
    liquidity_events: List[Dict[str, Any]]
    enable_mc: bool
    mc_runs: int
    enable_taxes: bool
    effective_tax_rate_pct: float
    inflation_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scenario':
        return cls(**data)


# Gordon Goss Brand Colors (Rolex-inspired)
BRAND_PRIMARY = "#003d29"      # Deep forest green (Rolex green)
BRAND_SECONDARY = "#c9a961"    # Champagne gold

# Configuration Constants
CURRENT_AGE = 30
RETIREMENT_AGE = 65
END_AGE = 95
CURRENT_BALANCE = 100000
CONTRIB_AMOUNT = 500
NOMINAL_RETURN_PCT = 7.0
RETURN_STDEV_PCT = 15.0
INFLATION_PCT = 3.0
FEE_PCT = 0.5
WITHDRAWAL_PCT = 4.0
WITHDRAWAL_REAL_AMOUNT = 50000
ENABLE_MC = True
MC_RUNS = 1000
MC_SEED = 42
CURRENCY = "USD"
SCENARIOS_FILE = Path("scenarios.json")
# Default house sale example values (used for initial template events)
HOUSE_SALE_AGE = 66
HOUSE_SALE_NET = 250000
HOUSE_SALE_PRICE = 500000
HOUSE_SALE_COSTS = 50000
HOUSE_PURCHASE_AGE = 40
HOUSE_PURCHASE_PRICE = 400000
HOUSE_PURCHASE_DOWNPAYMENT = 80000
    
def apply_liquidity_events(
    age: int,
    events: List[LiquidityEvent]
) -> tuple[float, List[str], float]:
    """
    Calculate net liquidity events for a given age.
    Returns (net_amount, labels_list, event_taxes)

    Note: Amounts should already be signed correctly:
    - Positive for inflows
    - Negative for outflows
    Only processes events where enabled=True
    """
    net = 0.0
    labels = []
    event_taxes = 0.0
    
    for event in events:
        # Skip disabled events
        if not event.enabled:
            continue
            
        # Check if event applies this age
        if event.start_age <= age <= event.end_age:
            if event.recurrence == "One-time":
                # One-time events only apply at start_age
                if age == event.start_age:
                    amount = event.amount
                    # Amount is already signed correctly (negative for debits)
                    net += amount
                    labels.append(event.label)
                    
                    # Calculate taxes if taxable and has positive value (credit/inflow)
                    # Debits are negative so they won't be taxed
                    if event.taxable and amount > 0:
                        event_taxes += amount * (event.tax_rate / 100.0)
            else:
                # Recurring events (Annual or Monthly)
                amount = event.amount
                if event.recurrence == "Monthly":
                    amount *= 12  # Annual aggregate
                # Amount is already signed correctly (negative for debits)
                net += amount
                labels.append(event.label)
                
                # Calculate taxes if taxable and has positive value (credit/inflow)
                # Debits are negative so they won't be taxed
                if event.taxable and amount > 0:
                    event_taxes += amount * (event.tax_rate / 100.0)
    
    return net, labels, event_taxes


def build_timeline(
    scenario: Scenario,
    liquidity_events: List[LiquidityEvent],
    show_real: bool = True
) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Build deterministic timeline from current age to end age.
    
    Returns:
        (timeline_df, metrics_dict)
    """

    rows = []
    # Initialize
    balance_nominal = scenario.current_balance
    cpi_index = 1.0
    inflation_rate = scenario.inflation_pct / 100.0
    inflation_enabled = getattr(scenario, 'inflation_enabled', True)
    nominal_return = scenario.nominal_return_pct / 100.0
    fee_rate = scenario.fee_pct / 100.0
    tax_rate = scenario.effective_tax_rate_pct / 100.0 if scenario.enable_taxes else 0.0
    prior_year_end_balance = balance_nominal
    first_shortfall_age = None

    for age in range(scenario.current_age, scenario.end_age + 1):
        start_balance = balance_nominal

        # Contributions (stop after retirement)
        contributions = 0.0
        if age < scenario.retirement_age:
            contributions = scenario.contrib_amount
            if scenario.contrib_cadence == "Monthly":
                contributions *= 12

        # Liquidity events
        liquidity_net, _, liquidity_event_taxes = apply_liquidity_events(age, liquidity_events)

        # Withdrawals (start at retirement)
        withdrawals = 0.0
        if age >= scenario.retirement_age:
            if scenario.withdrawal_method == "Fixed % of prior-year end balance":
                withdrawal_pct = scenario.withdrawal_pct / 100.0
                # Percentage is always annual, regardless of frequency
                withdrawals = prior_year_end_balance * withdrawal_pct
            else:
                real_amount = scenario.withdrawal_real_amount
                # Inflation only applies to future years, not initial capital
                if inflation_enabled:
                    # For the first year, cpi_index is 1.0 (no inflation)
                    withdrawals = real_amount * cpi_index
                else:
                    withdrawals = real_amount
                # For fixed real amount, multiply by 12 if monthly
                if scenario.withdrawal_frequency == "Monthly":
                    withdrawals *= 12
        # (No Streamlit/UI debug code here — function must be pure computation)
        # Fees
        fees = start_balance * fee_rate

        # Taxes (from withdrawals and liquidity events)
        taxes = liquidity_event_taxes
        if scenario.enable_taxes:
            taxes += withdrawals * tax_rate

        # Growth (deterministic)
        balance_after_cashflows = (
            start_balance + contributions + liquidity_net - withdrawals - fees - taxes
        )

        growth = balance_after_cashflows * nominal_return
        end_balance_nominal = balance_after_cashflows + growth
        if inflation_enabled:
            if age == scenario.current_age:
                cpi_index = 1.0
            end_balance_real = end_balance_nominal / cpi_index
        else:
            end_balance_real = end_balance_nominal

        rows.append(TimelineRow(
            age=age,
            start_balance_nominal=start_balance,
            contributions=contributions,
            liquidity_net=liquidity_net,
            withdrawals=withdrawals,
            fees=fees,
            taxes=taxes,
            growth=growth,
            end_balance_nominal=end_balance_nominal,
            cpi_index=cpi_index,
            end_balance_real=end_balance_real
        ))

        # Check for first shortfall (when balance goes negative)
        if first_shortfall_age is None and end_balance_nominal < 0:
            first_shortfall_age = age

        # Update for next iteration
        prior_year_end_balance = end_balance_nominal
        balance_nominal = end_balance_nominal
        if inflation_enabled and age != scenario.current_age:
            cpi_index *= (1 + inflation_rate)

    # Convert to DataFrame
    df = pd.DataFrame([asdict(row) for row in rows])

    # Metrics
    terminal_nominal = df.iloc[-1]['end_balance_nominal']
    terminal_real = df.iloc[-1]['end_balance_real']

    metrics = {
        'terminal_nominal': terminal_nominal,
        'terminal_real': terminal_real,
        'first_shortfall_age': first_shortfall_age,
        'probability_no_shortfall': None,
        'median_terminal': None,
        'p10_terminal': None,
        'p90_terminal': None,
    }

    return df, metrics


def run_monte_carlo(
    scenario: Scenario,
    liquidity_events: List[LiquidityEvent],
    runs: int = 1000,
    seed: int = MC_SEED
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation with variable returns.
    
    Returns metrics including probability of success.
    """
    np.random.seed(seed)
    
    inflation_rate = scenario.inflation_pct / 100.0
    mean_return = scenario.nominal_return_pct / 100.0
    stdev_return = scenario.return_stdev_pct / 100.0
    fee_rate = scenario.fee_pct / 100.0
    tax_rate = scenario.effective_tax_rate_pct / 100.0 if scenario.enable_taxes else 0.0
    
    num_years = scenario.end_age - scenario.current_age + 1
    
    # Pre-generate all random returns
    returns = np.random.normal(mean_return, stdev_return, size=(runs, num_years))
    
    terminal_values = []
    min_balances = []
    
    # Paths for percentile bands (optional)
    all_paths = []
    
    for run_idx in range(runs):
        balance_nominal = scenario.current_balance
        cpi_index = 1.0
        prior_year_end_balance = balance_nominal
        
        path = []
        min_balance = balance_nominal
        
        for year_idx, age in enumerate(range(scenario.current_age, scenario.end_age + 1)):
            start_balance = balance_nominal
            
            # Contributions
            contributions = 0.0
            if age < scenario.retirement_age:
                contributions = scenario.contrib_amount
                if scenario.contrib_cadence == "Monthly":
                    contributions *= 12
            
            # Liquidity events
            liquidity_net, _, liquidity_event_taxes = apply_liquidity_events(age, liquidity_events)
            
            # Withdrawals
            withdrawals = 0.0
            if age >= scenario.retirement_age:
                if scenario.withdrawal_method == "Fixed % of prior-year end balance":
                    withdrawal_pct = scenario.withdrawal_pct / 100.0
                    withdrawals = prior_year_end_balance * withdrawal_pct
                    
                    # Apply frequency - convert to annual amount
                    if scenario.withdrawal_frequency == "Monthly":
                        withdrawals *= 12  # Monthly rate × 12 = Annual amount
                else:
                    real_amount = scenario.withdrawal_real_amount
                    withdrawals = real_amount * cpi_index
                    
                    # Apply frequency - convert to annual amount
                    if scenario.withdrawal_frequency == "Monthly":
                        withdrawals *= 12  # Monthly amount × 12 = Annual amount
            
            # Fees
            fees = start_balance * fee_rate
            
            # Taxes (from withdrawals and liquidity events)
            taxes = liquidity_event_taxes
            if scenario.enable_taxes:
                taxes += withdrawals * tax_rate
            
            # Growth with random return
            balance_after_cashflows = (
                start_balance + contributions + liquidity_net - withdrawals - fees - taxes
            )
            
            growth = balance_after_cashflows * returns[run_idx, year_idx]
            end_balance_nominal = balance_after_cashflows + growth
            
            min_balance = min(min_balance, end_balance_nominal)
            path.append(end_balance_nominal / cpi_index)  # Real values
            
            prior_year_end_balance = end_balance_nominal
            balance_nominal = end_balance_nominal
            cpi_index *= (1 + inflation_rate)
        
        terminal_values.append(balance_nominal)
        min_balances.append(min_balance)
        all_paths.append(path)
    
    # Calculate metrics
    terminal_values = np.array(terminal_values)
    min_balances = np.array(min_balances)
    
    probability_no_shortfall = np.mean(min_balances >= 0)
    median_terminal = np.median(terminal_values)
    p10_terminal = np.percentile(terminal_values, 10)
    p90_terminal = np.percentile(terminal_values, 90)
    
    # Percentile bands (P10, P50, P90 over time)
    all_paths = np.array(all_paths)
    p10_path = np.percentile(all_paths, 10, axis=0)
    p50_path = np.percentile(all_paths, 50, axis=0)
    p90_path = np.percentile(all_paths, 90, axis=0)
    
    return {
        'probability_no_shortfall': probability_no_shortfall,
        'median_terminal': median_terminal,
        'p10_terminal': p10_terminal,
        'p90_terminal': p90_terminal,
        'p10_path': p10_path,
        'p50_path': p50_path,
        'p90_path': p90_path,
    }


def solve_safe_withdrawal_rate(
    scenario: Scenario,
    liquidity_events: List[LiquidityEvent],
    tolerance: float = 0.01,
    max_iterations: int = 50
) -> Optional[float]:
    """
    Binary search to find the maximum withdrawal % where balance never goes negative.
    
    Returns safe withdrawal rate as percentage.
    """
    if scenario.withdrawal_method != "Fixed % of prior-year end balance":
        return None  # Only applicable for percentage-based withdrawals
    
    low, high = 0.0, 20.0  # Search between 0% and 20%
    best_rate = 0.0
    
    # Debug list to track iterations
    debug_info = []
    
    for iteration in range(max_iterations):
        mid = (low + high) / 2.0
        
        # Test this withdrawal rate
        test_scenario = Scenario(**scenario.to_dict())
        test_scenario.withdrawal_pct = mid
        
        df, metrics = build_timeline(test_scenario, liquidity_events, show_real=True)
        
        # Check if any year goes negative
        min_balance = df['end_balance_nominal'].min()
        
        if min_balance >= 0:
            # Success, try higher
            best_rate = mid
            low = mid
            result = "✓ solvent"
        else:
            # Failed, try lower
            high = mid
            result = "✗ negative"
        
        debug_info.append(f"Iter {iteration+1}: {mid:.4f}% → min_balance=${min_balance:,.0f} ({result})")
        
        if high - low < tolerance:
            break
    
    # Store debug info in session state for display
    if 'swr_debug' not in st.session_state:
        st.session_state.swr_debug = []
    st.session_state.swr_debug = debug_info
    
    return best_rate


# ============================================================================
# EXPORT HELPERS
# ============================================================================

def export_csv(df: pd.DataFrame) -> bytes:
    """Export timeline DataFrame to CSV bytes."""
    return df.to_csv(index=False).encode('utf-8')


def export_chart_png(fig: go.Figure) -> Optional[bytes]:
    """Export Plotly figure to PNG bytes."""
    try:
        img_bytes = fig.to_image(format="png", width=1200, height=600)
        return img_bytes
    except (ValueError, ImportError):
        # Kaleido not installed
        return None


def save_scenarios(scenarios: Dict[str, Scenario]):
    """Save scenarios to JSON file."""
    data = {name: scenario.to_dict() for name, scenario in scenarios.items()}
    SCENARIOS_FILE.write_text(json.dumps(data, indent=2))


def load_scenarios() -> Dict[str, Scenario]:
    """Load scenarios from JSON file."""
    if not SCENARIOS_FILE.exists():
        return {}
    
    data = json.loads(SCENARIOS_FILE.read_text())
    return {name: Scenario.from_dict(scenario_data) for name, scenario_data in data.items()}


# ============================================================================
# UI HELPERS
# ============================================================================

def create_default_events() -> List[Dict[str, Any]]:
    """Create default liquidity events."""
    return [
        {
            'type': 'Credit',
            'label': 'Sell House',
            'start_age': HOUSE_SALE_AGE,
            'end_age': HOUSE_SALE_AGE,
            'amount': HOUSE_SALE_NET,
            'recurrence': 'One-time',
            'enabled': True,
            'taxable': False,
            'tax_rate': 0.0
        }
    ]


def show_liquidity_events_page(planning_end_age: int = END_AGE):
    """Full-screen page for managing liquidity events."""
    st.markdown("## Liquidity Events Management")
    st.markdown("Configure one-time and recurring cash inflows and outflows for your retirement plan.")
    
    # Initialize session state for saved and draft data
    if 'events_data' not in st.session_state:
        st.session_state.events_data = create_default_events()
    
    if 'events_draft' not in st.session_state:
        st.session_state.events_draft = st.session_state.events_data.copy()
    
    # Display events table using draft data
    try:
        if st.session_state.events_draft:
            events_df = pd.DataFrame(st.session_state.events_draft)
        else:
            # Create empty template with one row (use planning_end_age as sensible default)
            events_df = pd.DataFrame([{
                'enabled': True,
                'type': 'Credit',
                'label': '',
                'start_age': 65,
                'end_age': planning_end_age,
                'amount': 0.0,
                'recurrence': 'One-time',
                'taxable': False,
                'tax_rate': 0.0
            }])
        
        # Ensure only expected columns are present
        expected_columns = ['enabled', 'type', 'label', 'start_age', 'end_age', 'amount', 'recurrence', 'taxable', 'tax_rate']
        if 'enabled' not in events_df.columns:
            events_df['enabled'] = True
        events_df = events_df[[col for col in expected_columns if col in events_df.columns]]
        
        # Auto-populate end_age for one-time events (for display purposes)
        for idx in range(len(events_df)):
            if events_df.iloc[idx].get('recurrence') == 'One-time':
                start_age = events_df.iloc[idx].get('start_age')
                if pd.notna(start_age):
                    events_df.at[idx, 'end_age'] = start_age
        
        # Display debits as negative values in the table
        display_df = events_df.copy()
        for idx in range(len(display_df)):
            if display_df.iloc[idx].get('type', '').lower() == 'debit':
                # Make sure debits are shown as negative
                display_df.at[idx, 'amount'] = -abs(display_df.iloc[idx]['amount'])
            else:
                # Make sure credits are shown as positive
                display_df.at[idx, 'amount'] = abs(display_df.iloc[idx]['amount'])
        
        # Use data editor - don't auto-save on every change
        edited_df = st.data_editor(
            display_df,
            num_rows="dynamic",
            width="stretch",
            key="liquidity_events_editor",
            column_config={
                "enabled": st.column_config.CheckboxColumn(
                    "Active",
                    default=True,
                    help="Uncheck to disable this event without deleting it"
                ),
                "type": st.column_config.SelectboxColumn(
                    "Type",
                    options=["Credit", "Debit"],
                    required=True,
                    help="Credit = money coming in, Debit = money going out"
                ),
                "label": st.column_config.TextColumn("Label", required=True, max_chars=50),
                "start_age": st.column_config.NumberColumn("Start Age", min_value=0, max_value=110, required=True),
                "end_age": st.column_config.NumberColumn(
                    "End Age", 
                    min_value=0, 
                    max_value=110, 
                    required=False, 
                    help="End age for recurring events (grayed out for one-time events)"
                ),
                "amount": st.column_config.NumberColumn(
                    "Amount", 
                    format="$%.2f", 
                    required=True,
                    help="Enter the amount per period (monthly/annual). Debits will automatically be negative."
                ),
                "recurrence": st.column_config.SelectboxColumn(
                    "Recurrence",
                    options=["One-time", "Annual", "Monthly"],
                    required=True,
                    help="Monthly amounts will be multiplied by 12 to get annual total"
                ),
                "taxable": st.column_config.CheckboxColumn("Taxable?", default=False),
                "tax_rate": st.column_config.NumberColumn(
                    "Tax Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    format="%.2f%%",
                    default=0.0,
                    help="Tax rate for this specific event (0% = tax-free)"
                )
            },
            column_order=["enabled", "type", "recurrence", "label", "start_age", "end_age", "amount", "taxable", "tax_rate"],
            hide_index=True
        )
        
        st.caption("**Tip**: For One-time events, End Age is automatically set to Start Age. For Monthly events, enter the monthly amount (e.g., $10,000/month will be calculated as $120,000/year). Debit amounts will be converted to negative values when you click Save.")
        st.markdown("---")
        
        # Save button to apply changes
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            if st.button("Save Events", type="primary", width="stretch"):
                # Process and validate edited data (robust parsing)
                def _parse_number(val, default=0.0):
                    try:
                        if val is None or (isinstance(val, float) and np.isnan(val)):
                            return default
                        if isinstance(val, str):
                            s = val.replace('$', '').replace(',', '').strip()
                            return float(s) if s != '' else default
                        return float(val)
                    except Exception:
                        return default

                validated_data = []
                for idx in range(len(edited_df)):
                    try:
                        row = edited_df.iloc[idx].to_dict()

                        # Required keys present
                        if not all(k in row for k in ['type', 'label', 'start_age', 'amount', 'recurrence']):
                            continue

                        # Skip empty label rows
                        if not str(row.get('label', '')).strip():
                            continue

                        # Parse numeric fields robustly
                        start_age = int(_parse_number(row.get('start_age'), default=planning_end_age))
                        end_age = int(_parse_number(row.get('end_age', start_age), default=planning_end_age))
                        amount = _parse_number(row.get('amount'), default=0.0)
                        tax_rate = _parse_number(row.get('tax_rate', 0.0), default=0.0)

                        recurrence = row.get('recurrence', 'One-time') or 'One-time'

                        # For One-time events, force end_age to equal start_age
                        if recurrence == 'One-time':
                            end_age = start_age
                        # If this is a recurring event but end_age is not set or <= start_age, assume full planning horizon
                        elif end_age <= start_age:
                            end_age = planning_end_age

                        # Normalize amount sign based on type
                        typ = str(row.get('type', 'Debit'))
                        if typ.lower() == 'debit':
                            amount = -abs(amount)
                        else:  # Credit
                            amount = abs(amount)

                        validated_row = {
                            'enabled': bool(row.get('enabled', True)),
                            'type': typ,
                            'label': str(row.get('label', '')).strip(),
                            'start_age': start_age,
                            'end_age': end_age,
                            'amount': amount,
                            'recurrence': recurrence,
                            'taxable': bool(row.get('taxable', False)),
                            'tax_rate': float(tax_rate)
                        }

                        validated_data.append(validated_row)
                    except Exception:
                        # skip malformed rows
                        continue

                # Save to session state
                st.session_state.events_data = validated_data
                st.session_state.events_draft = validated_data.copy()
                st.success(f"Saved {len(validated_data)} events!")
                st.rerun()
        
        with col3:
            if st.button("Reset", width="stretch"):
                st.session_state.events_draft = st.session_state.events_data.copy()
                st.rerun()
        
        
        # Back button
        st.markdown("---")
        if st.button("Back to Dashboard", use_container_width=False):
            st.session_state.page = "dashboard"
            st.rerun()
            
    except Exception as e:
        st.error(f"Error in liquidity events table: {str(e)}")
        st.info("Click 'Reset' to restore last saved state")



def show_scenarios_page():
    """Full-screen page for managing saved scenarios."""
    st.markdown("## Scenario Management")
    st.markdown("Manage your saved retirement planning scenarios.")
    
    # Load saved scenarios
    if 'saved_scenarios' not in st.session_state:
        st.session_state.saved_scenarios = load_scenarios()
    
    saved_scenarios = st.session_state.saved_scenarios
    
    if not saved_scenarios:
        st.info("No saved scenarios yet. Return to the dashboard to create and save your first scenario.")
    else:
        # Initialize selected scenario in session state
        if 'selected_scenario_for_action' not in st.session_state:
            st.session_state.selected_scenario_for_action = None
        
        # Create DataFrame with key scenario details and selection checkbox
        scenarios_data = []
        for name, scenario in saved_scenarios.items():
            scenarios_data.append({
                'Select': name == st.session_state.selected_scenario_for_action,
                'Name': name,
                'Current Age': scenario.current_age,
                'Retirement Age': scenario.retirement_age,
                'End Age': scenario.end_age,
                'Current Balance': scenario.current_balance,
                'Withdrawal Method': scenario.withdrawal_method,
                'Monte Carlo': scenario.enable_mc,
                'Taxes Enabled': scenario.enable_taxes
            })
        
        scenarios_df = pd.DataFrame(scenarios_data)
        
        # Use data_editor to allow checkbox selection
        edited_df = st.data_editor(
            scenarios_df,
            use_container_width=True,
            disabled=['Name', 'Current Age', 'Retirement Age', 'End Age', 'Current Balance', 'Withdrawal Method', 'Monte Carlo', 'Taxes Enabled'],
            column_config={
                'Select': st.column_config.CheckboxColumn(
                    'Select',
                    help="Check to select scenario for Load/Delete actions",
                    default=False
                ),
                'Name': st.column_config.TextColumn('Name', width='medium'),
                'Current Balance': st.column_config.NumberColumn('Current Balance', format="$%.2f"),
                'Monte Carlo': st.column_config.CheckboxColumn('Monte Carlo'),
                'Taxes Enabled': st.column_config.CheckboxColumn('Taxes Enabled')
            },
            hide_index=True,
            key="scenarios_editor"
        )
        
        # Determine which scenario is selected (only one should be selected)
        selected_rows = edited_df[edited_df['Select'] == True]
        if len(selected_rows) > 0:
            st.session_state.selected_scenario_for_action = selected_rows.iloc[0]['Name']
        else:
            st.session_state.selected_scenario_for_action = None
        
        st.markdown("---")
        st.info("**Tip**: Check the box next to a scenario to enable Load/Delete buttons")
        
        # Load and Delete controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.session_state.selected_scenario_for_action:
                st.write(f"**Selected:** {st.session_state.selected_scenario_for_action}")
            else:
                st.write("**Selected:** None")
        
        with col2:
            if st.button("Load Scenario", type="primary", use_container_width=True, 
                        disabled=st.session_state.selected_scenario_for_action is None):
                if st.session_state.selected_scenario_for_action:
                    scenario = saved_scenarios[st.session_state.selected_scenario_for_action]
                    
                    # Update all session state values from the scenario
                    st.session_state.current_age = scenario.current_age
                    st.session_state.retirement_age = scenario.retirement_age
                    st.session_state.end_age = scenario.end_age
                    st.session_state.current_balance = scenario.current_balance
                    st.session_state.contrib_amount = scenario.contrib_amount
                    st.session_state.contrib_cadence = scenario.contrib_cadence
                    st.session_state.nominal_return_pct = scenario.nominal_return_pct
                    st.session_state.return_stdev_pct = scenario.return_stdev_pct
                    st.session_state.inflation_pct = scenario.inflation_pct
                    st.session_state.fee_pct = scenario.fee_pct
                    st.session_state.withdrawal_method = scenario.withdrawal_method
                    st.session_state.withdrawal_pct = scenario.withdrawal_pct
                    st.session_state.withdrawal_real_amount = scenario.withdrawal_real_amount
                    st.session_state.withdrawal_frequency = scenario.withdrawal_frequency
                    st.session_state.events_data = scenario.liquidity_events
                    st.session_state.events_draft = scenario.liquidity_events.copy()
                    st.session_state.enable_mc = scenario.enable_mc
                    st.session_state.mc_runs = scenario.mc_runs
                    st.session_state.enable_taxes = scenario.enable_taxes
                    st.session_state.effective_tax_rate_pct = scenario.effective_tax_rate_pct
                    st.session_state.inflation_enabled = getattr(scenario, 'inflation_enabled', True)
                    
                    st.success(f"Loaded scenario: {st.session_state.selected_scenario_for_action}")
                    st.session_state.selected_scenario_for_action = None  # Reset selection
                    st.session_state.page = "dashboard"
                    st.rerun()
        
        with col3:
            if st.button("Delete Scenario", use_container_width=True,
                        disabled=st.session_state.selected_scenario_for_action is None):
                if st.session_state.selected_scenario_for_action:
                    deleted_name = st.session_state.selected_scenario_for_action
                    # Remove from dict and save
                    del saved_scenarios[deleted_name]
                    st.session_state.saved_scenarios = saved_scenarios
                    save_scenarios(saved_scenarios)
                    st.session_state.selected_scenario_for_action = None  # Reset selection
                    st.success(f"🗑️ Deleted scenario: {deleted_name}")
                    st.rerun()
    
    # Back button
    st.markdown("---")
    if st.button("Back to Dashboard", use_container_width=False):
        st.session_state.page = "dashboard"
        st.rerun()


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(
        page_title="Gordon Goss | Retirement Planning",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for Gordon Goss branding
    st.markdown("""
        <style>
        /* Gordon Goss Brand Styling */
        .main {
            background-color: #ffffff;
        }
        
        /* Header styling */
        h1, h2, h3 {
            color: #003d29 !important;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-weight: 300;
            letter-spacing: 0.5px;
        }
        
        h1 {
            font-size: 2.5rem !important;
            margin-bottom: 0.5rem !important;
            border-bottom: 2px solid #c9a961;
            padding-bottom: 1rem;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #f8f8f8;
            border-right: 1px solid #e0e0e0;
        }
        
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: #003d29 !important;
        }
        
        /* Metrics styling */
        [data-testid="stMetricValue"] {
            color: #003d29 !important;
            font-weight: 400;
        }
        
        [data-testid="stMetricLabel"] {
            color: #2c2c2c !important;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Button styling */
        .stButton > button {
            background-color: #003d29;
            color: white;
            border: none;
            padding: 0.5rem 2rem;
            font-weight: 400;
            letter-spacing: 0.5px;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background-color: #00563a;
            box-shadow: 0 2px 8px rgba(0, 61, 41, 0.3);
        }
        
        /* Download button styling */
        .stDownloadButton > button {
            background-color: #c9a961;
            color: #1a1a1a;
            border: none;
            padding: 0.5rem 2rem;
            font-weight: 400;
            letter-spacing: 0.5px;
        }
        
        .stDownloadButton > button:hover {
            background-color: #d4b56d;
            box-shadow: 0 2px 8px rgba(201, 169, 97, 0.4);
        }
        
        /* Dataframe styling */
        .dataframe {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 0.9rem;
        }
        
        /* Info/warning box styling */
        .stAlert {
            border-left: 4px solid #c9a961;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background-color: #f8f8f8;
            border: 1px solid #e0e0e0;
            color: #003d29;
            font-weight: 400;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Gordon Goss Header
    st.markdown("""
        <div style="text-align: left; padding: 1rem 0 2rem 0;">
            <h1 style="margin: 0; color: #003d29; font-weight: 300; letter-spacing: 2px;">
                GORDON GOSS
            </h1>
            <p style="margin: 0; color: #c9a961; font-size: 1.1rem; letter-spacing: 3px; font-weight: 300;">
                RETIREMENT PLANNING
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize page routing
    if 'page' not in st.session_state:
        st.session_state.page = "dashboard"
    
    # Check if we should show the liquidity events page
    if st.session_state.page == "liquidity_events":
        planning_end_age = st.session_state.get('liquidity_events_end_age', END_AGE)
        show_liquidity_events_page(planning_end_age)
        return  # Exit main function after showing liquidity events page
    
    # Check if we should show the scenarios management page
    if st.session_state.page == "scenarios":
        show_scenarios_page()
        return  # Exit main function after showing scenarios page
    
    # Load saved scenarios
    saved_scenarios = load_scenarios()
    
    # Sidebar
    st.sidebar.markdown("### Configuration")
    
    # Currency
    st.sidebar.markdown(f"**Currency:** {CURRENCY}")
    
    # Basic inputs
    st.sidebar.markdown("#### Personal Information")
    
    # Use session state values if they exist, otherwise use defaults
    current_age_default = st.session_state.get('current_age', CURRENT_AGE)
    current_age = st.sidebar.slider(
        "Current age",
        min_value=18,
        max_value=80,
        value=current_age_default,
        key="current_age",
        help="Your current age"
    )
    
    retirement_age_default = st.session_state.get('retirement_age', max(RETIREMENT_AGE, current_age))
    retirement_age = st.sidebar.slider(
        "Retirement age",
        min_value=current_age,
        max_value=80,
        value=max(retirement_age_default, current_age),
        key="retirement_age",
        help="Age when you plan to retire"
    )
    
    end_age_default = st.session_state.get('end_age', max(END_AGE, retirement_age))
    end_age = st.sidebar.slider(
        "End age (planning horizon)",
        min_value=retirement_age,
        max_value=110,
        value=max(end_age_default, retirement_age),
        key="end_age",
        help="Plan until this age"
    )
    
    # Financial inputs
    st.sidebar.markdown("#### Current Portfolio")
    
    # Initialize defaults only on first load
    if 'current_balance' not in st.session_state:
        st.session_state.current_balance = float(CURRENT_BALANCE)
    if 'contrib_amount' not in st.session_state:
        st.session_state.contrib_amount = float(CONTRIB_AMOUNT)
    
    current_balance = st.sidebar.number_input(
        "Current combined balance ($)",
        min_value=0.0,
        value=st.session_state.current_balance,
        step=10000.0,
        key="current_balance_input",
        help="Your total portfolio value today"
    )
    # Sync the value to session state
    st.session_state.current_balance = current_balance
    
    st.sidebar.markdown("#### Ongoing Contributions")
    contrib_amount = st.sidebar.number_input(
        "Contribution amount ($)",
        min_value=0.0,
        value=st.session_state.contrib_amount,
        step=100.0,
        key="contrib_amount_input",
        help="How much you contribute each period"
    )
    # Sync the value to session state
    st.session_state.contrib_amount = contrib_amount

    
    contrib_cadence = st.sidebar.radio(
        "Contribution cadence",
        options=["Monthly", "Annual"],
        index=0 if st.session_state.get('contrib_cadence', 'Monthly') == 'Monthly' else 1,
        key="contrib_cadence",
        help="Contributions stop automatically at retirement"
    )
    
    # Returns & inflation
    st.sidebar.markdown("#### Market Assumptions")
    nominal_return_pct_default = st.session_state.get('nominal_return_pct', NOMINAL_RETURN_PCT)
    nominal_return_pct = st.sidebar.slider(
        "Expected nominal return (%)",
        min_value=0.0,
        max_value=20.0,
        value=nominal_return_pct_default,
        step=0.1,
        key="nominal_return_pct",
        help="Expected annual return before inflation"
    )
    
    inflation_pct_default = st.session_state.get('inflation_pct', INFLATION_PCT)
    inflation_pct = st.sidebar.slider(
        "Inflation (%)",
        min_value=0.0,
        max_value=10.0,
        value=inflation_pct_default,
        step=0.1,
        key="inflation_pct",
        help="Expected annual inflation"
    )
    inflation_enabled = st.sidebar.toggle(
        "Apply Inflation",
        value=st.session_state.get('inflation_enabled', True),
        key="inflation_enabled",
        help="Toggle to include inflation in all future years. If off, inflation is ignored in calculations."
    )
    
    fee_pct_default = st.session_state.get('fee_pct', FEE_PCT)
    fee_pct = st.sidebar.slider(
        "Annual fee/expense drag (%)",
        min_value=0.0,
        max_value=5.0,
        value=fee_pct_default,
        step=0.05,
        key="fee_pct",
        help="Annual fees and expenses"
    )
    

    # Withdrawal settings
    st.sidebar.markdown("#### Withdrawal Settings")
    withdrawal_method_default = st.session_state.get('withdrawal_method', "Fixed % of prior-year end balance")
    withdrawal_method = st.sidebar.radio(
        "Withdrawal method",
        options=["Fixed % of prior-year end balance", "Fixed real dollars"],
        index=0 if withdrawal_method_default == "Fixed % of prior-year end balance" else 1,
        key="withdrawal_method",
        help="Choose withdrawal calculation method"
    )
    # Default frequency to ensure variable is always defined
    withdrawal_frequency = "Annual"
    
    if withdrawal_method == "Fixed % of prior-year end balance":
        withdrawal_pct_default = st.session_state.get('withdrawal_pct', WITHDRAWAL_PCT)
        withdrawal_pct = st.sidebar.slider(
            "Withdrawal % of balance",
            min_value=0.0,
            max_value=20.0,
            value=withdrawal_pct_default,
            step=0.1,
            key="withdrawal_pct",
            help="Percentage of prior year's ending balance to withdraw annually"
        )
        
        # Calculate and display the nominal annual withdrawal amount in USD
        calculated_annual_withdrawal = current_balance * (withdrawal_pct / 100.0)
        st.sidebar.number_input(
            "Calculated Annual Withdrawal (Year 1)",
            value=calculated_annual_withdrawal,
            disabled=True,
            format="%.2f",
            help=f"Based on {withdrawal_pct}% of current balance (${current_balance:,.2f})"
        )
        
        withdrawal_real_amount = WITHDRAWAL_REAL_AMOUNT  # Keep default for scenario saving
    else:
        withdrawal_pct = WITHDRAWAL_PCT  # Keep default for scenario saving
        withdrawal_frequency_default = st.session_state.get('withdrawal_frequency', 'Annual')
        withdrawal_frequency = st.sidebar.radio(
            "Withdrawal frequency",
            options=["Annual", "Monthly"],
            index=0 if withdrawal_frequency_default == "Annual" else 1,
            key="withdrawal_frequency",
            help="How often withdrawals occur"
        )
        frequency_label = "monthly" if withdrawal_frequency == "Monthly" else "annual"
        withdrawal_real_amount_default = st.session_state.get('withdrawal_real_amount', float(WITHDRAWAL_REAL_AMOUNT))
        withdrawal_real_amount = st.sidebar.number_input(
            f"Fixed real {frequency_label} withdrawal ($)",
            min_value=0.0,
            value=withdrawal_real_amount_default,
            step=1000.0,
            key="withdrawal_real_amount",
            help="Inflation-adjusted purchasing power"
        )
    
    # Set default frequency if not already set
    if 'withdrawal_frequency' not in locals():
        withdrawal_frequency = "Annual"

    # Liquidity events - Initialize session state
    if 'events_data' not in st.session_state:
        st.session_state.events_data = create_default_events()
    if 'liquidity_events_end_age' not in st.session_state:
        st.session_state.liquidity_events_end_age = end_age
    
    # Liquidity Events Management Button
    st.sidebar.markdown("#### Liquidity Events")
    if st.sidebar.button("Manage Liquidity Events", width="stretch"):
        st.session_state.page = "liquidity_events"
        st.session_state.liquidity_events_end_age = end_age
        st.rerun()
    
    # Convert saved events to LiquidityEvent objects
    liquidity_events = []
    if st.session_state.events_data:
        for event_dict in st.session_state.events_data:
            try:
                liquidity_events.append(LiquidityEvent.from_dict(event_dict))
            except Exception as e:
                st.sidebar.error(f"Error loading event: {str(e)}")
    
    # Options & toggles
    st.sidebar.markdown("#### Display Options")
    show_real_default = st.session_state.get('show_real_radio', 'Real')
    show_real = st.sidebar.radio(
        "Show values",
        options=["Real", "Nominal"],
        index=0 if show_real_default == "Real" else 1,
        key="show_real_radio"
    ) == "Real"
    
    # Initialize session state for persistent settings across page navigation
    if 'enable_mc' not in st.session_state:
        st.session_state.enable_mc = ENABLE_MC
    if 'mc_runs' not in st.session_state:
        st.session_state.mc_runs = MC_RUNS
    if 'effective_tax_rate_pct' not in st.session_state:
        st.session_state.effective_tax_rate_pct = 0.0
    
    enable_mc = st.sidebar.checkbox(
        "Enable Monte Carlo",
        value=st.session_state.enable_mc,
        key="enable_mc_checkbox",
        help="Run probabilistic simulation"
    )
    st.session_state.enable_mc = enable_mc
    
    mc_runs = st.session_state.mc_runs
    if enable_mc:
        mc_runs = st.sidebar.slider(
            "Monte Carlo runs",
            min_value=100,
            max_value=5000,
            value=st.session_state.mc_runs,
            key="mc_runs_slider",
            step=100
        )
        st.session_state.mc_runs = mc_runs
    
    return_stdev_pct_default = st.session_state.get('return_stdev_pct', RETURN_STDEV_PCT)
    return_stdev_pct = st.sidebar.slider(
        "Return volatility (stdev, %)",
        min_value=0.0,
        max_value=50.0,
        value=return_stdev_pct_default,
        step=0.5,
        key="return_stdev_pct",
        help="Standard deviation for Monte Carlo simulation"
    )
    
    # Withdrawal tax rate
    st.sidebar.markdown("#### Withdrawal Tax Rate")
    effective_tax_rate_pct = st.sidebar.number_input(
        "Withdrawal tax rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=st.session_state.effective_tax_rate_pct,
        key="effective_tax_rate_input",
        step=1.0,
        help="Tax rate applied to withdrawals"
    )
    st.session_state.effective_tax_rate_pct = effective_tax_rate_pct
    
    enable_taxes = effective_tax_rate_pct > 0
    
    # Scenario controls
    st.sidebar.markdown("#### Scenario Management")

    # Save scenario (max 5)
    scenario_a_name = st.sidebar.text_input(
        "Scenario Name",
        value="Scenario A",
        key="scenario_a_name"
    )
    
    # Add compact styling for sidebar buttons only
    st.sidebar.markdown("""
    <style>
    /* Compact sidebar scenario buttons */
    div[data-testid="stSidebar"] button[kind="primary"],
    div[data-testid="stSidebar"] button[kind="secondary"] {
        font-size: 11px !important;
        padding: 0.5rem 0.3rem !important;
        line-height: 1.2 !important;
        min-height: 2.5rem !important;
        max-height: 2.5rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: clip !important;
        width: 100% !important;
    }
    div[data-testid="stSidebar"] button p {
        font-size: 11px !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }
    div[data-testid="stSidebar"] div[data-testid="column"] {
        padding: 0 2px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    save_clicked = st.sidebar.button("Save Scenario", key="save_scenario_btn", use_container_width=True)
    manage_clicked = st.sidebar.button("Manage Scenarios", key="manage_scenarios_btn", use_container_width=True)
    
    # Handle Save Scenario
    if save_clicked:
        if len(saved_scenarios) >= 5 and scenario_a_name not in saved_scenarios:
            st.sidebar.warning("Maximum 5 scenarios allowed. Delete one to save a new scenario.")
        else:
            # Ensure only allowed Literal values are passed
            scenario_a = Scenario(
                name=scenario_a_name,
                current_age=current_age,
                retirement_age=retirement_age,
                end_age=end_age,
                current_balance=current_balance,
                contrib_amount=contrib_amount,
                contrib_cadence=contrib_cadence,
                nominal_return_pct=nominal_return_pct,
                return_stdev_pct=return_stdev_pct,
                inflation_pct=inflation_pct,
                fee_pct=fee_pct,
                withdrawal_method=withdrawal_method,
                withdrawal_pct=withdrawal_pct,
                withdrawal_real_amount=withdrawal_real_amount,
                withdrawal_frequency=withdrawal_frequency,
                liquidity_events=[e.to_dict() for e in liquidity_events],
                enable_mc=enable_mc,
                mc_runs=mc_runs,
                enable_taxes=enable_taxes,
                effective_tax_rate_pct=effective_tax_rate_pct,
                inflation_enabled=inflation_enabled
            )
            saved_scenarios[scenario_a_name] = scenario_a
            save_scenarios(saved_scenarios)
            st.sidebar.success(f"Saved '{scenario_a_name}'!")
    
    # Handle Manage Scenarios
    if manage_clicked:
        st.session_state.page = "scenarios"
        st.rerun()

    # Compare scenarios section
    st.sidebar.markdown("#### Compare Scenarios")
    compare_names = [name for name in saved_scenarios.keys()]
    compare_a = st.sidebar.selectbox("Scenario 1", ["<none>"] + compare_names, key="compare_a")
    compare_b = st.sidebar.selectbox("Scenario 2", ["<none>"] + [n for n in compare_names if n != compare_a], key="compare_b")
    
    # Initialize comparison state in session_state if not present
    if 'comparison_active' not in st.session_state:
        st.session_state.comparison_active = False
    if 'comparison_scenario_a' not in st.session_state:
        st.session_state.comparison_scenario_a = None
    if 'comparison_scenario_b' not in st.session_state:
        st.session_state.comparison_scenario_b = None
    
    # Compare and Clear buttons stacked vertically
    compare_triggered = st.sidebar.button("Compare Scenarios", key="compare_btn", use_container_width=True)
    # Always show clear button but disable when not comparing
    clear_triggered = st.sidebar.button("Clear Scenarios", key="clear_comparison_btn", use_container_width=True, 
                                         disabled=not st.session_state.comparison_active)

    # Handle Clear button FIRST (before Compare updates state)
    if clear_triggered and st.session_state.comparison_active:
        st.session_state.comparison_active = False
        st.session_state.comparison_scenario_a = None
        st.session_state.comparison_scenario_b = None
        st.rerun()
    
    # Update comparison state when Compare button is clicked
    if compare_triggered:
        if compare_a != "<none>" and compare_b != "<none>":
            st.session_state.comparison_active = True
            st.session_state.comparison_scenario_a = compare_a
            st.session_state.comparison_scenario_b = compare_b
            st.rerun()
        else:
            # Clear comparison if button clicked but invalid selection
            st.session_state.comparison_active = False
            st.session_state.comparison_scenario_a = None
            st.session_state.comparison_scenario_b = None
    
    # Use persistent comparison state
    compare_scenarios = st.session_state.comparison_active
    scenario_a = None
    scenario_b = None
    if compare_scenarios:
        if (st.session_state.comparison_scenario_a in saved_scenarios and 
            st.session_state.comparison_scenario_b in saved_scenarios):
            scenario_a = saved_scenarios[st.session_state.comparison_scenario_a]
            scenario_b = saved_scenarios[st.session_state.comparison_scenario_b]
        else:
            # Scenarios no longer exist, clear comparison
            st.session_state.comparison_active = False
            compare_scenarios = False
    
    # Tax Rate Reference Legend
    st.sidebar.markdown("---")
    with st.sidebar.expander("Tax Rate Reference Guide"):
        st.markdown("""
        **Common Tax Rates by Jurisdiction:**
        
        **Tax-Free Havens:**
        - **Cayman Islands**: 0%
        - **Bermuda**: 0%
        - **Monaco**: 0%
        - **UAE (Dubai)**: 0%
        
        **Low Tax Countries:**
        - **Singapore**: ~10-15%
        - **Hong Kong**: ~15%
        - **Switzerland**: ~15-20%
        - **Portugal (NHR)**: ~10%
        
        **Moderate Tax Countries:**
        - **Spain**: ~19-26%
        - **Italy**: ~23-43%
        - **UK**: ~20-45%
        - **Germany**: ~25-45%
        
        **High Tax Countries:**
        - **USA**: ~25-37% (Federal + State)
        - **Canada**: ~30-50%
        - **France**: ~30-45%
        - **Sweden**: ~30-55%
        
        **How to Use:**
        - Set **Withdrawal Tax Rate** for retirement income
        - Set **Tax Rate (%)** per liquidity event for specific transactions
        - Enable **Taxable?** checkbox for events subject to tax
        """)
    
    # Admin Panel (placeholder for future advanced features)
    st.sidebar.markdown("---")
    with st.sidebar.expander("Admin Panel", expanded=False):
        st.markdown(f"""
        **Version {__version__} - October 21, 2025**
        
        **Recent Updates (v2.1.0):**
        
        **UI/UX Improvements:**
        - Age/Year toggle on projection graphs (X-axis switch)
        - Annual Cashflow Analysis - now open by default
        - Debug Monitor - now closed by default
        - Admin Panel - now closed by default
        
        **Liquidity Events:**
        - Auto-populate end age for one-time events
        - Simplified event types (Credit/Debit)
        - Recurrence field moved next to Type for better UX
        - Removed emojis from UI elements
        
        **Bug Fixes:**
        - First Shortfall Age detection now works correctly
        - Fixed calculation to properly detect negative balances
        
        **Notes:**
        - Graph displays end-of-year balances (industry standard)
        - Percentage-based withdrawals adjust with balance
        - Use "Fixed real dollars" to see First Shortfall Age
        
        **Future Features:**
        - Batch scenario imports/exports
        - Advanced debugging tools
        - Custom calculation overrides
        - Data integrity checks
        """)
    
    # Build current scenario A (only if not comparing - otherwise use saved scenario)
    if not compare_scenarios:
        scenario_a = Scenario(
            name=scenario_a_name,
            current_age=current_age,
            retirement_age=retirement_age,
            end_age=end_age,
            current_balance=current_balance,
            contrib_amount=contrib_amount,
            contrib_cadence=contrib_cadence,
            nominal_return_pct=nominal_return_pct,
            return_stdev_pct=return_stdev_pct,
            inflation_pct=inflation_pct,
            fee_pct=fee_pct,
            withdrawal_method=withdrawal_method,
            withdrawal_pct=withdrawal_pct,
            withdrawal_real_amount=withdrawal_real_amount,
            withdrawal_frequency=withdrawal_frequency,
            liquidity_events=[e.to_dict() for e in liquidity_events],
            enable_mc=enable_mc,
            mc_runs=mc_runs,
            enable_taxes=enable_taxes,
            effective_tax_rate_pct=effective_tax_rate_pct,
            inflation_enabled=inflation_enabled
        )
    
    # Get liquidity events for scenario A
    if compare_scenarios:
        liquidity_events_a = [LiquidityEvent.from_dict(e) for e in scenario_a.liquidity_events]
    else:
        liquidity_events_a = liquidity_events
    
    # Calculate timeline for Scenario A
    timeline_a, metrics_a = build_timeline(scenario_a, liquidity_events_a, show_real)
    
    # Monte Carlo for Scenario A (use scenario's own MC settings when comparing)
    mc_results_a = None
    mc_enabled_a = scenario_a.enable_mc if compare_scenarios else enable_mc
    mc_runs_a = scenario_a.mc_runs if compare_scenarios else mc_runs
    if mc_enabled_a:
        mc_results_a = run_monte_carlo(scenario_a, liquidity_events_a, mc_runs_a)
        metrics_a.update(mc_results_a)
    
    # Calculate for Scenario B if comparing
    timeline_b = None
    metrics_b = None
    mc_results_b = None
    
    if compare_scenarios and scenario_b:
        events_b = [LiquidityEvent.from_dict(e) for e in scenario_b.liquidity_events]
        timeline_b, metrics_b = build_timeline(scenario_b, events_b, show_real)
        
        if scenario_b.enable_mc:
            mc_results_b = run_monte_carlo(scenario_b, events_b, scenario_b.mc_runs)
            metrics_b.update(mc_results_b)
    
    # ========================================================================
    # MAIN CONTENT
    # ========================================================================
    
    # KPI Row
    st.markdown("## Key Performance Metrics")
    
    # Primary Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Terminal Value (Real)",
            value=f"${metrics_a['terminal_real']:,.0f}",
            help="Inflation-adjusted portfolio value at end of planning horizon"
        )
    
    with col2:
        st.metric(
            label="Terminal Value (Nominal)",
            value=f"${metrics_a['terminal_nominal']:,.0f}",
            help="Actual dollar value at end of planning horizon without inflation adjustment"
        )
    
    with col3:
        prob_value = f"{metrics_a['probability_no_shortfall']*100:.1f}%" if metrics_a['probability_no_shortfall'] is not None else "N/A"
        st.metric(
            label="Probability of Success",
            value=prob_value,
            help="Percentage of Monte Carlo simulations where portfolio never goes negative"
        )
    
    with col4:
        shortfall_value = str(metrics_a['first_shortfall_age']) if metrics_a['first_shortfall_age'] else "None"
        st.metric(
            label="First Shortfall Age",
            value=shortfall_value,
            help="Age when portfolio balance first goes negative, or None if solvent throughout"
        )
    
    # Monte Carlo Analysis (if enabled)
    if enable_mc and mc_results_a:
        with st.expander("Monte Carlo Analysis", expanded=True):
            mc_col1, mc_col2, mc_col3 = st.columns(3)
            
            with mc_col1:
                st.metric(
                    label="Median Terminal (MC)",
                    value=f"${mc_results_a['median_terminal']:,.0f}",
                    help="50th percentile outcome across all Monte Carlo simulations"
                )
            
            with mc_col2:
                st.metric(
                    label="P10 Terminal (MC)",
                    value=f"${mc_results_a['p10_terminal']:,.0f}",
                    help="10th percentile - only 10% of outcomes are worse than this value"
                )
            
            with mc_col3:
                st.metric(
                    label="P90 Terminal (MC)",
                    value=f"${mc_results_a['p90_terminal']:,.0f}",
                    help="90th percentile - only 10% of outcomes are better than this value"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Safe Withdrawal Rate Button
            col_swr1, col_swr2, col_swr3 = st.columns([1, 1, 1])
            with col_swr2:
                if st.button("Calculate Safe Withdrawal Rate", width="stretch"):
                    if scenario_a.withdrawal_method == "Fixed % of prior-year end balance":
                        with st.spinner("Calculating optimal withdrawal rate..."):
                            swr = solve_safe_withdrawal_rate(scenario_a, liquidity_events_a)
                            st.success(f"**Safe Withdrawal Rate: {swr:.2f}%**")
                            st.caption("Maximum withdrawal rate where portfolio remains solvent")
                    else:
                        st.warning("SWR solver requires '% of prior-year balance' withdrawal method")
    
    # Comparison metrics
    if compare_scenarios and scenario_b and metrics_b:
        st.markdown("### Scenario Comparison")
        comp_data = {
            "Metric": ["Terminal (Real)", "Terminal (Nominal)", "First Shortfall Age"],
            scenario_a.name: [
                f"${metrics_a['terminal_real']:,.0f}",
                f"${metrics_a['terminal_nominal']:,.0f}",
                str(metrics_a['first_shortfall_age']) if metrics_a['first_shortfall_age'] else "None"
            ],
            scenario_b.name: [
                f"${metrics_b['terminal_real']:,.0f}",
                f"${metrics_b['terminal_nominal']:,.0f}",
                str(metrics_b['first_shortfall_age']) if metrics_b['first_shortfall_age'] else "None"
            ]
        }
        
        if metrics_a['probability_no_shortfall'] is not None or metrics_b['probability_no_shortfall'] is not None:
            comp_data["Metric"].append("Probability of Success")
            comp_data[scenario_a.name].append(
                f"{metrics_a['probability_no_shortfall']*100:.1f}%" if metrics_a['probability_no_shortfall'] is not None else "N/A"
            )
            comp_data[scenario_b.name].append(
                f"{metrics_b['probability_no_shortfall']*100:.1f}%" if metrics_b['probability_no_shortfall'] is not None else "N/A"
            )
        
        # Ensure all columns have the same length
        max_len = max(len(comp_data["Metric"]), len(comp_data[scenario_a.name]), len(comp_data[scenario_b.name]))
        for key in comp_data.keys():
            while len(comp_data[key]) < max_len:
                comp_data[key].append("N/A")
        
        st.dataframe(pd.DataFrame(comp_data), width="stretch", hide_index=True)
    
    # Main Chart
    st.markdown("## Portfolio Balance Projection")
    
    # Add X-axis toggle (Age vs Year)
    col_left, col_right = st.columns([4, 1])
    with col_right:
        x_axis_mode = st.radio(
            "X-Axis:",
            options=["Age", "Year"],
            index=0,
            horizontal=True,
            key="x_axis_toggle",
            help="Switch between Age and Calendar Year"
        )
    
    # Calculate year values (assuming current age = current year 2025)
    from datetime import datetime
    current_year = datetime.now().year
    age_to_year_offset = current_year - current_age
    
    # Prepare event grouping for chart (needed before creating traces)
    # Separate one-time and recurring events FOR SCENARIO A
    one_time_events = []
    recurring_events = []
    
    for event in liquidity_events_a:
        if not event.enabled:
            continue
        if event.recurrence == "One-time":
            one_time_events.append(event)
        else:
            recurring_events.append(event)
    
    # Group ALL events (one-time + recurring) by age for hover information FOR SCENARIO A
    all_events_by_age = {}
    for event in liquidity_events_a:
        if not event.enabled:
            continue
            
        # Determine which ages this event affects
        if event.recurrence == "One-time":
            ages_affected = [event.start_age]
        else:
            ages_affected = range(event.start_age, event.end_age + 1)
        
        for age in ages_affected:
            if age not in all_events_by_age:
                all_events_by_age[age] = []
            all_events_by_age[age].append(event)
    
    # Group ONE-TIME events by age for markers on the chart
    one_time_by_age = {}
    for event in one_time_events:
        age = event.start_age
        if age not in one_time_by_age:
            one_time_by_age[age] = []
        one_time_by_age[age].append(event)
    
    # Prepare event grouping for SCENARIO B if comparing
    one_time_events_b = []
    recurring_events_b = []
    all_events_by_age_b = {}
    one_time_by_age_b = {}
    
    if compare_scenarios and scenario_b:
        events_b_list = [LiquidityEvent.from_dict(e) for e in scenario_b.liquidity_events]
        
        for event in events_b_list:
            if not event.enabled:
                continue
            if event.recurrence == "One-time":
                one_time_events_b.append(event)
            else:
                recurring_events_b.append(event)
        
        # Group ALL events by age for hover
        for event in events_b_list:
            if not event.enabled:
                continue
            
            if event.recurrence == "One-time":
                ages_affected = [event.start_age]
            else:
                ages_affected = range(event.start_age, event.end_age + 1)
            
            for age in ages_affected:
                if age not in all_events_by_age_b:
                    all_events_by_age_b[age] = []
                all_events_by_age_b[age].append(event)
        
        # Group ONE-TIME events by age for markers
        for event in one_time_events_b:
            age = event.start_age
            if age not in one_time_by_age_b:
                one_time_by_age_b[age] = []
            one_time_by_age_b[age].append(event)
    
    fig = go.Figure()
    
    # Scenario A
    balance_col = 'end_balance_real' if show_real else 'end_balance_nominal'
    value_type = 'Real' if show_real else 'Nominal'
    
    # Build custom hover text that includes event information
    hover_texts = []
    for _, row in timeline_a.iterrows():
        age = int(row['age'])
        balance = row[balance_col]
        
        # Start with base hover text - include scenario name if comparing
        if compare_scenarios and scenario_b:
            hover_parts = [
                f"<b>═══ {scenario_a.name.upper()} ═══</b>",
                f"Age: {age}",
                f"Balance ({value_type}): ${balance:,.0f}"
            ]
        else:
            hover_parts = [
                f"<b>Portfolio Balance</b>",
                f"Age: {age}",
                f"Balance ({value_type}): ${balance:,.0f}"
            ]
        
        # Add event information if there are any events at this age
        if age in all_events_by_age:
            events_at_age = all_events_by_age[age]
            hover_parts.append("")
            hover_parts.append("<b>Liquidity Events:</b>")
            
            total_inflow = 0.0
            total_outflow = 0.0
            
            for event in events_at_age:
                amount = event.amount
                recur_label = event.recurrence
                if event.recurrence == "Monthly":
                    amount *= 12
                    recur_label = "Annual"  # Display as Annual since we show the yearly total
                
                if amount > 0:
                    total_inflow += amount
                else:
                    total_outflow += amount
                
                event_type = "↑" if amount > 0 else "↓"
                recur_text = f" ({recur_label})" if event.recurrence != "One-time" else ""
                hover_parts.append(f"  {event_type} {event.label}: ${abs(amount):,.0f}{recur_text}")
            
            # Add net summary
            net_amount = total_inflow + total_outflow
            if net_amount > 0:
                hover_parts.append(f"  <b>Net: +${net_amount:,.0f}</b>")
            elif net_amount < 0:
                hover_parts.append(f"  <b>Net: -${abs(net_amount):,.0f}</b>")
            else:
                hover_parts.append(f"  <b>Net: $0</b>")
        
        hover_texts.append("<br>".join(hover_parts))
    
    # Prepare x-axis values based on toggle
    if x_axis_mode == "Year":
        x_values_a = [age + age_to_year_offset for age in timeline_a['age']]
    else:
        x_values_a = timeline_a['age']
    
    fig.add_trace(go.Scatter(
        x=x_values_a,
        y=timeline_a[balance_col],
        mode='lines',
        name=f"{scenario_a.name} ({value_type})",
        line=dict(color='#003d29', width=2.5),
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>"
    ))
    
    # Monte Carlo bands for Scenario A (only if not comparing)
    if enable_mc and mc_results_a and not compare_scenarios:
        ages = list(range(scenario_a.current_age, scenario_a.end_age + 1))
        
        # Convert to years if needed
        if x_axis_mode == "Year":
            x_mc_values = [age + age_to_year_offset for age in ages]
        else:
            x_mc_values = ages
        
        x_label = "Year" if x_axis_mode == "Year" else "Age"
        
        fig.add_trace(go.Scatter(
            x=x_mc_values,
            y=mc_results_a['p90_path'],
            mode='lines',
            name='90th Percentile',
            line=dict(color='#c9a961', width=1, dash='dot'),
            showlegend=True,
            hovertemplate=(
                "<b>90th Percentile</b><br>" +
                f"{x_label}: %{{x}}<br>" +
                f"Balance ({value_type}): $%{{y:,.0f}}<br>" +
                "<extra></extra>"
            )
        ))
        
        fig.add_trace(go.Scatter(
            x=x_mc_values,
            y=mc_results_a['p10_path'],
            mode='lines',
            name='10th Percentile',
            line=dict(color='#c9a961', width=1, dash='dot'),
            fill='tonexty',
            fillcolor='rgba(201, 169, 97, 0.15)',
            showlegend=True,
            hovertemplate=(
                "<b>10th Percentile</b><br>" +
                f"{x_label}: %{{x}}<br>" +
                f"Balance ({value_type}): $%{{y:,.0f}}<br>" +
                "<extra></extra>"
            )
        ))
    
    # Scenario B
    if compare_scenarios and timeline_b is not None and scenario_b is not None:
        # Build custom hover text for scenario B including its events
        hover_texts_b = []
        for _, row in timeline_b.iterrows():
            age = int(row['age'])
            balance = row[balance_col]
            
            hover_parts_b = [
                f"<b>═══ {scenario_b.name.upper()} ═══</b>",
                f"Age: {age}",
                f"Balance ({value_type}): ${balance:,.0f}"
            ]
            
            # Add event information if there are any events at this age for scenario B
            if age in all_events_by_age_b:
                events_at_age_b = all_events_by_age_b[age]
                hover_parts_b.append("")
                hover_parts_b.append("<b>Liquidity Events:</b>")
                
                total_inflow = 0.0
                total_outflow = 0.0
                
                for event in events_at_age_b:
                    amount = event.amount
                    recur_label = event.recurrence
                    if event.recurrence == "Monthly":
                        amount *= 12
                        recur_label = "Annual"  # Display as Annual since we show the yearly total
                    
                    if amount > 0:
                        total_inflow += amount
                    else:
                        total_outflow += amount
                    
                    event_type = "↑" if amount > 0 else "↓"
                    recur_text = f" ({recur_label})" if event.recurrence != "One-time" else ""
                    hover_parts_b.append(f"  {event_type} {event.label}: ${abs(amount):,.0f}{recur_text}")
                
                # Add net summary
                net_amount = total_inflow + total_outflow
                if net_amount > 0:
                    hover_parts_b.append(f"  <b>Net: +${net_amount:,.0f}</b>")
                elif net_amount < 0:
                    hover_parts_b.append(f"  <b>Net: -${abs(net_amount):,.0f}</b>")
                else:
                    hover_parts_b.append(f"  <b>Net: $0</b>")
            
            hover_texts_b.append("<br>".join(hover_parts_b))
        
        # Prepare x-axis for scenario B
        if x_axis_mode == "Year":
            x_values_b = [age + age_to_year_offset for age in timeline_b['age']]
        else:
            x_values_b = timeline_b['age']
        
        fig.add_trace(go.Scatter(
            x=x_values_b,
            y=timeline_b[balance_col],
            mode='lines',
            name=f"{scenario_b.name} ({value_type})",
            line=dict(color='#2c2c2c', width=2, dash='dash'),
            hovertext=hover_texts_b,
            hovertemplate="%{hovertext}<extra></extra>"
        ))
    
    # Retirement age vertical line
    retirement_x = retirement_age + age_to_year_offset if x_axis_mode == "Year" else retirement_age
    fig.add_vline(
        x=retirement_x,
        line_dash="dash",
        line_color="#c9a961",
        annotation_text="Retirement",
        annotation_position="top",
        annotation_font_color="#003d29"
    )
    
    # Add zero line to clearly show when portfolio goes negative
    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color="#8b2635",
        line_width=1,
        opacity=0.5
    )
    
    # Plot ONE marker per age for ONE-TIME events only
    for age, events in one_time_by_age.items():
        age_row = timeline_a[timeline_a['age'] == age]
        if age_row.empty:
            continue
            
        # Get the balance at this age on the chart line
        balance_on_line = age_row.iloc[0][balance_col]
        
        # Calculate total for one-time events at this age
        total_amount = sum(e.amount for e in events)
        
        # Determine marker color
        if total_amount > 0:
            marker_color = '#c9a961'  # Gold for inflow
        elif total_amount < 0:
            marker_color = '#8b2635'  # Burgundy for outflow
        else:
            marker_color = '#6b6b6b'  # Gray
        
        # Create label
        if len(events) == 1:
            label_text = events[0].label[:12]
        else:
            label_text = f"{len(events)} Events"
        
        # Simple hover for the marker (detailed info comes from portfolio line hover)
        event_names = ", ".join([e.label for e in events])
        
        # Calculate x position based on mode
        marker_x = age + age_to_year_offset if x_axis_mode == "Year" else age
        x_label_text = "Year" if x_axis_mode == "Year" else "Age"
        
        fig.add_trace(go.Scatter(
            x=[marker_x],
            y=[balance_on_line],
            mode='markers+text',
            name=label_text,
            marker=dict(
                size=14,
                color=marker_color,
                symbol='diamond',
                line=dict(color='#003d29', width=2)
            ),
            text=[label_text],
            textposition='top center',
            textfont=dict(size=9, color='#003d29', family="Helvetica Neue, Arial, sans-serif"),
            hovertemplate=f"<b>{event_names}</b><br>{x_label_text} {marker_x}<extra></extra>",
            hoverlabel=dict(
                bgcolor='#f8f8f8',
                font_size=12,
                font_family="Helvetica Neue, Arial, sans-serif",
                bordercolor=marker_color
            ),
            showlegend=False
        ))
    
    # Plot markers for Scenario B one-time events
    if compare_scenarios and timeline_b is not None:
        for age, events in one_time_by_age_b.items():
            age_row = timeline_b[timeline_b['age'] == age]
            if age_row.empty:
                continue
                
            # Get the balance at this age on scenario B's line
            balance_on_line = age_row.iloc[0][balance_col]
            
            # Calculate total for one-time events at this age
            total_amount = sum(e.amount for e in events)
            
            # Determine marker color (use slightly different colors for scenario B)
            if total_amount > 0:
                marker_color = '#ffd700'  # Bright gold for inflow
            elif total_amount < 0:
                marker_color = '#dc143c'  # Crimson for outflow
            else:
                marker_color = '#808080'  # Gray
            
            # Create label
            if len(events) == 1:
                label_text = events[0].label[:12]
            else:
                label_text = f"{len(events)} Events"
            
            # Simple hover for the marker
            event_names = ", ".join([e.label for e in events])
            
            # Calculate x position based on mode
            marker_x_b = age + age_to_year_offset if x_axis_mode == "Year" else age
            x_label_text = "Year" if x_axis_mode == "Year" else "Age"
            
            fig.add_trace(go.Scatter(
                x=[marker_x_b],
                y=[balance_on_line],
                mode='markers+text',
                name=f"{label_text} (B)",
                marker=dict(
                    size=14,
                    color=marker_color,
                    symbol='square',  # Use square for scenario B to differentiate
                    line=dict(color='#2c2c2c', width=2)
                ),
                text=[label_text],
                textposition='bottom center',
                textfont=dict(size=9, color='#2c2c2c', family="Helvetica Neue, Arial, sans-serif"),
                hovertemplate=f"<b>{scenario_b.name}: {event_names}</b><br>{x_label_text} {marker_x_b}<extra></extra>",
                hoverlabel=dict(
                    bgcolor='#f0f0f0',
                    font_size=12,
                    font_family="Helvetica Neue, Arial, sans-serif",
                    bordercolor=marker_color
                ),
                showlegend=False
            ))
    
    # Add recurring events legend box (annotation)
    # When comparing scenarios, create TWO separate legend boxes for clarity
    if compare_scenarios and scenario_b and (recurring_events or recurring_events_b):
        # SCENARIO A LEGEND (Left side)
        if recurring_events:
            legend_lines_a = [f"<b>{scenario_a.name}</b>", "<b>Recurring Events:</b>"]
            
            # Separate credits and debits
            credits = [e for e in recurring_events if e.amount > 0]
            debits = [e for e in recurring_events if e.amount < 0]
            
            if credits:
                legend_lines_a.append("<b>Credits:</b>")
                for event in credits:
                    amount = event.amount
                    freq = "yr"  # Always show per year since we display annual totals
                    if event.recurrence == "Monthly":
                        amount *= 12
                    amount_str = f"${abs(amount):,.0f}"
                    legend_lines_a.append(f"  + {event.label}: {amount_str}/{freq}")
                    legend_lines_a.append(f"    (Age {event.start_age}-{event.end_age})")
            
            if debits:
                legend_lines_a.append("<b>Debits:</b>")
                for event in debits:
                    amount = event.amount
                    freq = "yr"  # Always show per year since we display annual totals
                    if event.recurrence == "Monthly":
                        amount *= 12
                    amount_str = f"${abs(amount):,.0f}"
                    legend_lines_a.append(f"  - {event.label}: {amount_str}/{freq}")
                    legend_lines_a.append(f"    (Age {event.start_age}-{event.end_age})")
            
            fig.add_annotation(
                xref="paper", yref="paper",
                x=0.02, y=0.02,
                xanchor='left', yanchor='bottom',
                text="<br>".join(legend_lines_a),
                showarrow=False,
                font=dict(size=10, family="Helvetica Neue, Arial, sans-serif", color="#2c2c2c"),
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='#003d29',
                borderwidth=2,
                borderpad=8,
                align='left'
            )
        
        # SCENARIO B LEGEND (Right side)
        if recurring_events_b:
            legend_lines_b = [f"<b>{scenario_b.name}</b>", "<b>Recurring Events:</b>"]
            
            # Separate credits and debits for scenario B
            credits_b = [e for e in recurring_events_b if e.amount > 0]
            debits_b = [e for e in recurring_events_b if e.amount < 0]
            
            if credits_b:
                legend_lines_b.append("<b>Credits:</b>")
                for event in credits_b:
                    amount = event.amount
                    freq = "yr"  # Always show per year since we display annual totals
                    if event.recurrence == "Monthly":
                        amount *= 12
                    amount_str = f"${abs(amount):,.0f}"
                    legend_lines_b.append(f"  + {event.label}: {amount_str}/{freq}")
                    legend_lines_b.append(f"    (Age {event.start_age}-{event.end_age})")
            
            if debits_b:
                legend_lines_b.append("<b>Debits:</b>")
                for event in debits_b:
                    amount = event.amount
                    freq = "yr"  # Always show per year since we display annual totals
                    if event.recurrence == "Monthly":
                        amount *= 12
                    amount_str = f"${abs(amount):,.0f}"
                    legend_lines_b.append(f"  - {event.label}: {amount_str}/{freq}")
                    legend_lines_b.append(f"    (Age {event.start_age}-{event.end_age})")
            
            fig.add_annotation(
                xref="paper", yref="paper",
                x=0.98, y=0.02,
                xanchor='right', yanchor='bottom',
                text="<br>".join(legend_lines_b),
                showarrow=False,
                font=dict(size=10, family="Helvetica Neue, Arial, sans-serif", color="#2c2c2c"),
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='#2c2c2c',
                borderwidth=2,
                borderpad=8,
                align='left'
            )
    
    # Single scenario legend (original behavior)
    elif recurring_events and not compare_scenarios:
        legend_lines = ["<b>Recurring Events:</b>"]
        
        # Separate credits and debits
        credits = [e for e in recurring_events if e.amount > 0]
        debits = [e for e in recurring_events if e.amount < 0]
        
        if credits:
            legend_lines.append("<b>Credits:</b>")
            for event in credits:
                amount = event.amount
                freq = "yr"  # Always show per year since we display annual totals
                if event.recurrence == "Monthly":
                    amount *= 12
                amount_str = f"${abs(amount):,.0f}"
                legend_lines.append(f"  + {event.label}: {amount_str}/{freq} (Age {event.start_age}-{event.end_age})")
        
        if debits:
            legend_lines.append("<b>Debits:</b>")
            for event in debits:
                amount = event.amount
                freq = "yr"  # Always show per year since we display annual totals
                if event.recurrence == "Monthly":
                    amount *= 12
                amount_str = f"${abs(amount):,.0f}"
                legend_lines.append(f"  - {event.label}: {amount_str}/{freq} (Age {event.start_age}-{event.end_age})")
        
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.98, y=0.02,
            xanchor='right', yanchor='bottom',
            text="<br>".join(legend_lines),
            showarrow=False,
            font=dict(size=10, family="Helvetica Neue, Arial, sans-serif", color="#2c2c2c"),
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='#003d29',
            borderwidth=2,
            borderpad=8,
            align='left'
        )
    
    x_axis_title_text = "Year" if x_axis_mode == "Year" else "Age"
    
    fig.update_layout(
        xaxis_title=x_axis_title_text,
        yaxis_title=f"Portfolio Balance ({CURRENCY})",
        hovermode='x unified',  # Show all traces at same x position
        height=550,  # Increased height to accommodate labels
        showlegend=True,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Helvetica Neue, Arial, sans-serif", color="#2c2c2c"),
        xaxis=dict(gridcolor='#e0e0e0', showgrid=True),
        yaxis=dict(
            gridcolor='#e0e0e0', 
            showgrid=True,
            rangemode='normal'  # Allow automatic ranging including negative values
        ),
        legend=dict(
            bgcolor='rgba(248, 248, 248, 0.9)',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        margin=dict(t=40, b=40, l=60, r=20)  # Add margin to prevent cutoff
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
    
    # Cashflow Chart - Improved Design
    st.markdown("## Annual Cashflow Analysis")
    with st.expander("View Detailed Cashflow Breakdown", expanded=True):
        st.markdown("**This chart shows all cash inflows and outflows by year.**")
        
        cashflow_fig = go.Figure()
        
        # Use same x-axis values as main chart
        x_values_cashflow = x_values_a  # Reuse the calculated values from main chart
        x_label_cashflow = "Year" if x_axis_mode == "Year" else "Age"
        
        # Contributions (green for inflows)
        cashflow_fig.add_trace(go.Bar(
            x=x_values_cashflow,
            y=timeline_a['contributions'],
            name='Contributions',
            marker_color='#00875a',  # Brighter green for better contrast
            hovertemplate=f'<b>Contributions</b><br>{x_label_cashflow}: %{{x}}<br>Amount: $%{{y:,.0f}}<extra></extra>'
        ))
        
        # Withdrawals (red/burgundy for outflows)
        cashflow_fig.add_trace(go.Bar(
            x=x_values_cashflow,
            y=-timeline_a['withdrawals'],
            name='Withdrawals',
            marker_color='#8b2635',  # Burgundy/wine red for contrast
            hovertemplate=f'<b>Withdrawals</b><br>{x_label_cashflow}: %{{x}}<br>Amount: -$%{{customdata:,.0f}}<extra></extra>',
            customdata=timeline_a['withdrawals']
        ))
        
        # Liquidity Events - split into inflows (positive) and outflows (negative)
        liquidity_inflows = timeline_a['liquidity_net'].clip(lower=0)  # Positive values only
        liquidity_outflows = timeline_a['liquidity_net'].clip(upper=0)  # Negative values only
        
        # Liquidity Inflows (gold - Gordon Goss accent)
        cashflow_fig.add_trace(go.Bar(
            x=x_values_cashflow,
            y=liquidity_inflows,
            name='Liquidity Inflows',
            marker_color='#c9a961',  # Gordon Goss gold
            hovertemplate=f'<b>Liquidity Inflows</b><br>{x_label_cashflow}: %{{x}}<br>Amount: $%{{y:,.0f}}<extra></extra>'
        ))
        
        # Liquidity Outflows (darker gold/bronze)
        cashflow_fig.add_trace(go.Bar(
            x=x_values_cashflow,
            y=liquidity_outflows,
            name='Liquidity Outflows',
            marker_color='#8b7355',  # Bronze/brown
            hovertemplate=f'<b>Liquidity Outflows</b><br>{x_label_cashflow}: %{{x}}<br>Amount: -$%{{customdata:,.0f}}<extra></extra>',
            customdata=abs(liquidity_outflows)
        ))
        
        # Fees (dark gray)
        cashflow_fig.add_trace(go.Bar(
            x=x_values_cashflow,
            y=-timeline_a['fees'],
            name='Fees',
            marker_color='#6b6b6b',
            hovertemplate=f'<b>Fees</b><br>{x_label_cashflow}: %{{x}}<br>Amount: -$%{{customdata:,.0f}}<extra></extra>',
            customdata=timeline_a['fees']
        ))
        
        # Taxes (darker red)
        cashflow_fig.add_trace(go.Bar(
            x=x_values_cashflow,
            y=-timeline_a['taxes'],
            name='Taxes',
            marker_color='#5c1a1a',
            hovertemplate=f'<b>Taxes</b><br>{x_label_cashflow}: %{{x}}<br>Amount: -$%{{customdata:,.0f}}<extra></extra>',
            customdata=timeline_a['taxes']
        ))
        
        cashflow_fig.update_layout(
            barmode='relative',
            xaxis_title=x_axis_title_text,
            yaxis_title=f"Annual Cashflow ({CURRENCY})",
            height=450,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="Helvetica Neue, Arial, sans-serif", color="#2c2c2c", size=12),
            xaxis=dict(
                gridcolor='#e0e0e0',
                showgrid=True,
                zeroline=True,
                zerolinecolor='#003d29',
                zerolinewidth=2
            ),
            yaxis=dict(
                gridcolor='#e0e0e0',
                showgrid=True,
                zeroline=True,
                zerolinecolor='#003d29',
                zerolinewidth=2
            ),
            legend=dict(
                bgcolor='rgba(248, 248, 248, 0.95)',
                bordercolor='#003d29',
                borderwidth=1,
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='center',
                x=0.5
            ),
            hovermode='x unified'
        )
        
        st.plotly_chart(cashflow_fig, use_container_width=True, config={'displayModeBar': True})
        
        # Summary statistics
        st.markdown("### Cashflow Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_contrib = timeline_a['contributions'].sum()
            st.metric("Total Contributions", f"${total_contrib:,.0f}")
        with col2:
            total_withdraw = timeline_a['withdrawals'].sum()
            st.metric("Total Withdrawals", f"${total_withdraw:,.0f}")
        with col3:
            total_fees = timeline_a['fees'].sum()
            st.metric("Total Fees", f"${total_fees:,.0f}")
        with col4:
            total_taxes = timeline_a['taxes'].sum()
            st.metric("Total Taxes", f"${total_taxes:,.0f}")
    
    # Timeline Table
    st.markdown("## Annual Timeline Analysis")
    
    if compare_scenarios and timeline_b is not None and scenario_b is not None:
        # COMPARISON TABLE: Show both scenarios side by side with deltas
        st.markdown(f"**Comparing: {scenario_a.name} vs {scenario_b.name}**")
        
        # Create comparison dataframe
        comp_timeline_df = pd.DataFrame({
            'Age': timeline_a['age'],
            
            # Scenario A columns
            f'{scenario_a.name} - End Balance (Nominal)': timeline_a['end_balance_nominal'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_a.name} - End Balance (Real)': timeline_a['end_balance_real'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_a.name} - Growth': timeline_a['growth'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_a.name} - Contributions': timeline_a['contributions'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_a.name} - Withdrawals': timeline_a['withdrawals'].apply(lambda x: f"${x:,.0f}"),
            
            # Scenario B columns
            f'{scenario_b.name} - End Balance (Nominal)': timeline_b['end_balance_nominal'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_b.name} - End Balance (Real)': timeline_b['end_balance_real'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_b.name} - Growth': timeline_b['growth'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_b.name} - Contributions': timeline_b['contributions'].apply(lambda x: f"${x:,.0f}"),
            f'{scenario_b.name} - Withdrawals': timeline_b['withdrawals'].apply(lambda x: f"${x:,.0f}"),
            
            # Delta columns (raw values for calculation)
            'Δ End Balance (Nominal)': (timeline_b['end_balance_nominal'] - timeline_a['end_balance_nominal']).apply(
                lambda x: f"${x:+,.0f}" if x != 0 else "$0"
            ),
            'Δ End Balance (Real)': (timeline_b['end_balance_real'] - timeline_a['end_balance_real']).apply(
                lambda x: f"${x:+,.0f}" if x != 0 else "$0"
            ),
        })
        
        st.dataframe(comp_timeline_df, width="stretch", hide_index=True)
        
    else:
        # SINGLE SCENARIO TABLE: Original detailed view
        display_df = timeline_a[[
            'age',
            'start_balance_nominal',
            'contributions',
            'liquidity_net',
            'withdrawals',
            'fees',
            'taxes',
            'growth',
            'end_balance_nominal',
            'cpi_index',
            'end_balance_real'
        ]].copy()
        
        # Format for display
        currency_cols = [
            'start_balance_nominal',
            'contributions',
            'liquidity_net',
            'withdrawals',
            'fees',
            'taxes',
            'growth',
            'end_balance_nominal',
            'end_balance_real'
        ]
        
        for col in currency_cols:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
        
        display_df['cpi_index'] = display_df['cpi_index'].apply(lambda x: f"{x:.4f}")
        
        st.dataframe(display_df, width="stretch", hide_index=True)
    
    # Export buttons
    st.markdown("## Export & Download")
    
    export_cols = st.columns(2)
    
    with export_cols[0]:
        csv_data = export_csv(timeline_a)
        st.download_button(
            label="Download Timeline (CSV)",
            data=csv_data,
            file_name=f"gordon_goss_timeline_{scenario_a.name}.csv",
            mime="text/csv"
        )
    
    with export_cols[1]:
        png_data = export_chart_png(fig)
        if png_data:
            st.download_button(
                label="Download Chart (PNG)",
                data=png_data,
                file_name=f"gordon_goss_chart_{scenario_a.name}.png",
                mime="image/png"
            )
        else:
            st.info("Install kaleido for PNG export: `pip install kaleido`")
    
    # ============================================================
    # DEBUG MONITOR (Real-time calculation verification)
    # ============================================================
    st.markdown("---")
    st.markdown("## Debug Monitor")
    
    with st.expander("**LIVE CALCULATION TRACKER** - Verify Math in Real-Time", expanded=False):
        st.markdown("**This panel updates automatically as you change parameters above. Watch the calculations update!**")
        st.markdown("---")
        
        # Show current configuration snapshot
        st.markdown("### Current Configuration")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Current Age", scenario_a.current_age)
            st.metric("Retirement Age", scenario_a.retirement_age)
            st.metric("End Age", scenario_a.end_age)
        with col2:
            st.metric("Starting Balance", f"${scenario_a.current_balance:,.0f}")
            st.metric("Contribution", f"${scenario_a.contrib_amount:,.0f}")
            st.metric("Contrib Cadence", scenario_a.contrib_cadence)
        with col3:
            st.metric("Nominal Return", f"{scenario_a.nominal_return_pct}%")
            st.metric("Inflation", f"{scenario_a.inflation_pct}%")
            st.metric("Fee Rate", f"{scenario_a.fee_pct}%")
        with col4:
            if scenario_a.withdrawal_method == "Fixed % of prior-year end balance":
                st.metric("Withdrawal %", f"{scenario_a.withdrawal_pct}%")
            else:
                st.metric("Withdrawal Amt", f"${scenario_a.withdrawal_real_amount:,.0f}")
            st.metric("Withdrawal Freq", scenario_a.withdrawal_frequency)
            st.metric("Withdrawal Tax", f"{effective_tax_rate_pct}%")
        
        st.markdown("---")
        st.markdown("### Sample Year: Detailed Step-by-Step Calculation")
        
        # Calculate one sample year at retirement age
        sample_age = scenario_a.retirement_age
        sample_row = timeline_a[timeline_a['age'] == sample_age]
        
        if not sample_row.empty:
            row = sample_row.iloc[0]
            
            # Get prior year balance
            if sample_age > scenario_a.current_age:
                prior_row = timeline_a[timeline_a['age'] == sample_age - 1]
                prior_balance = prior_row.iloc[0]['end_balance_nominal'] if not prior_row.empty else scenario_a.current_balance
            else:
                prior_balance = scenario_a.current_balance
            
            st.info(f"**Analyzing Age {sample_age} (First Year of Retirement)**")
            
            # Starting balance
            st.markdown("#### 1️⃣ Starting Balance")
            st.code(f"Starting Balance = ${row['start_balance_nominal']:,.2f}")
            st.caption(f"Note: This is the ending balance from age {sample_age - 1}")
            
            # Contributions
            st.markdown("#### 2️⃣ Contributions")
            contrib_calc = scenario_a.contrib_amount
            if sample_age < scenario_a.retirement_age:
                if scenario_a.contrib_cadence == "Monthly":
                    st.code(f"Contributions = ${scenario_a.contrib_amount:,.2f} × 12 (monthly cadence) = ${contrib_calc * 12:,.2f}")
                else:
                    st.code(f"Contributions = ${contrib_calc:,.2f} (annual cadence)")
                contrib_calc = contrib_calc * 12 if scenario_a.contrib_cadence == "Monthly" else contrib_calc
            else:
                st.code(f"Contributions = $0.00")
                st.caption("Contributions stop at retirement age")
                contrib_calc = 0
            st.caption(f"**Actual from timeline: ${row['contributions']:,.2f}**")
            
            # Check if matches
            if abs(contrib_calc - row['contributions']) < 0.01:
                st.success("Match!")
            else:
                st.error(f"Mismatch! Expected ${contrib_calc:,.2f}, got ${row['contributions']:,.2f}")
            
            # (Debug/verification panel removed to keep UI professional and avoid
            #  intermittent references to internal variables. Calculations are
            #  performed deterministically in build_timeline; use unit tests
            #  or a dedicated admin/debug page if deep inspection is required.)
        
        st.markdown("---")
        st.markdown("### Timeline Preview (First & Last 5 Years)")
        
        # Show first 5 years
        st.markdown("**First 5 Years:**")
        first_years = timeline_a.head(5).copy()
        first_years_display = first_years[['age', 'start_balance_nominal', 'contributions', 'liquidity_net', 
                                           'withdrawals', 'fees', 'taxes', 'growth', 'end_balance_nominal']].copy()
        
        # Format as currency
        for col in first_years_display.columns:
            if col != 'age':
                first_years_display[col] = first_years_display[col].apply(lambda x: f"${x:,.0f}")
        st.dataframe(first_years_display, width="stretch", hide_index=True)

        # Show last 5 years
        st.markdown("**Last 5 Years:**")
        last_years = timeline_a.tail(5).copy()
        last_years_display = last_years[['age', 'start_balance_nominal', 'contributions', 'liquidity_net', 
                                         'withdrawals', 'fees', 'taxes', 'growth', 'end_balance_nominal']].copy()
        for col in last_years_display.columns:
            if col != 'age':
                last_years_display[col] = last_years_display[col].apply(lambda x: f"${x:,.0f}")
        st.dataframe(last_years_display, width="stretch", hide_index=True)
        
        # Liquidity Events Debug
        if liquidity_events:
            st.markdown("---")
            st.markdown("### Liquidity Events Active in Timeline")
            for evt in liquidity_events:
                with st.container():
                    st.write(f"**{evt.label}** ({evt.type})")
                    st.write(f"  • Amount: ${evt.amount:,.2f}")
                    st.write(f"  • Active ages: {evt.start_age} to {evt.end_age}")
                    st.write(f"  • Recurrence: {evt.recurrence}")
                    st.write(f"  • Taxable: {evt.taxable} (Rate: {evt.tax_rate}%)")
                    
                    # Show when it applies
                    if evt.recurrence == "One-time":
                        st.caption(f"Applies ONCE at age {evt.start_age}")
                    elif evt.recurrence == "Monthly":
                        annual_amount = evt.amount * 12
                        st.caption(f"Applies EVERY YEAR from {evt.start_age} to {evt.end_age}, annualized to ${annual_amount:,.2f}/year")
                    else:
                        st.caption(f"Applies EVERY YEAR from {evt.start_age} to {evt.end_age}")
    
    # Admin Section - Detailed Calculation Breakdown
    st.markdown("---")
    st.markdown("## Administration")
    
    with st.expander("Show Detailed Calculation Breakdown", expanded=False):
        st.markdown("### Calculation Verification & Audit Trail")
        
        # Scenario Parameters
        with st.expander("Scenario Parameters", expanded=True):
            st.markdown("#### Input Configuration")
            params_data = {
                "Parameter": [
                    "Current Age", "Retirement Age", "End Age",
                    "Current Balance", "Contribution Amount", "Contribution Cadence",
                    "Expected Nominal Return", "Return Volatility (Stdev)", "Inflation Rate",
                    "Annual Fee/Expense Drag", "Withdrawal Method", "Withdrawal %/Amount",
                    "Withdrawal Frequency", "Withdrawal Tax Rate", "Monte Carlo Runs"
                ],
                "Value": [
                    scenario_a.current_age, scenario_a.retirement_age, scenario_a.end_age,
                    f"${scenario_a.current_balance:,.2f}", f"${scenario_a.contrib_amount:,.2f}", scenario_a.contrib_cadence,
                    f"{scenario_a.nominal_return_pct}%", f"{scenario_a.return_stdev_pct}%", f"{scenario_a.inflation_pct}%",
                    f"{scenario_a.fee_pct}%", scenario_a.withdrawal_method,
                    f"{scenario_a.withdrawal_pct}%" if scenario_a.withdrawal_method == "Fixed % of prior-year end balance" else f"${scenario_a.withdrawal_real_amount:,.2f}",
                    scenario_a.withdrawal_frequency,
                    f"{scenario_a.effective_tax_rate_pct}% (0% = tax-free)",
                    scenario_a.mc_runs if scenario_a.enable_mc else "Disabled"
                ]
            }
            st.dataframe(pd.DataFrame(params_data), hide_index=True, width="stretch")
        
        # Safe Withdrawal Rate Calculation Details
        if 'swr_debug' in st.session_state and st.session_state.swr_debug:
            with st.expander("Safe Withdrawal Rate Calculation Details", expanded=False):
                st.markdown("#### Binary Search Iterations")
                st.caption("Shows how the algorithm narrows down the maximum sustainable withdrawal rate:")
                for line in st.session_state.swr_debug:
                    st.code(line, language=None)
                
                st.markdown("""
                **Algorithm Explanation:**
                - Searches between 0% and 20% withdrawal rate
                - Tests each rate by simulating the full timeline
                - If portfolio stays positive: tries a higher rate
                - If portfolio goes negative: tries a lower rate
                - Converges to within 0.01% tolerance
                """)
        
        # Liquidity Events Detail
        with st.expander("Liquidity Events Configuration", expanded=True):
            st.markdown("#### All Configured Events")
            if liquidity_events:
                events_detail = []
                for evt in liquidity_events:
                    events_detail.append({
                        "Type": evt.type,
                        "Label": evt.label,
                        "Start Age": evt.start_age,
                        "End Age": evt.end_age,
                        "Amount": f"${evt.amount:,.2f}",
                        "Recurrence": evt.recurrence,
                        "Taxable": "Yes" if evt.taxable else "No",
                        "Tax Rate": f"{evt.tax_rate}%"
                    })
                st.dataframe(pd.DataFrame(events_detail), hide_index=True, width="stretch")
            else:
                st.info("No liquidity events configured")
        
        # Tax Configuration & Breakdown
        with st.expander("Tax Configuration & Breakdown", expanded=True):
            st.markdown("#### Tax Settings")
            tax_config = {
                "Tax Type": [
                    "Withdrawal Tax Rate",
                    "Per-Event Tax Rates",
                    "Tax Treatment"
                ],
                "Configuration": [
                    f"{effective_tax_rate_pct}% (applied to all retirement withdrawals)",
                    "Individual rates set per liquidity event (see table above)",
                    "Only taxable inflows are taxed; outflows/debts are NOT taxed"
                ]
            }
            st.dataframe(pd.DataFrame(tax_config), hide_index=True, width="stretch")
            
            st.markdown("#### Tax Calculation Methodology")
            st.markdown("""
            **Annual Tax Calculation:**
            ```
            Total Taxes (per year) = Withdrawal Taxes + Event Taxes
            
            Where:
              Withdrawal Taxes = Annual Withdrawals × Withdrawal Tax Rate
              
              Event Taxes = Σ (Taxable Event Amount × Event Tax Rate)
                           for all taxable events with positive amounts
            ```
            
            **Important Notes:**
            - **Taxed**: Withdrawals, taxable liquidity event inflows (positive amounts)
            - **NOT Taxed**: Contributions, fees, negative liquidity events (debts/outflows)
            - Each liquidity event can have its own tax rate (0-100%)
            - Default 0% = tax-free (Cayman Islands treatment)
            """)
            
            # Calculate tax breakdown
            total_withdrawal_taxes = 0.0
            total_event_taxes = 0.0
            
            for idx, row in timeline_a.iterrows():
                age = int(row['age'])
                year_taxes = row['taxes']
                
                # Withdrawal tax for this year
                if row['withdrawals'] > 0 and effective_tax_rate_pct > 0:
                    total_withdrawal_taxes += row['withdrawals'] * (effective_tax_rate_pct / 100.0)
                
                # Event taxes for this year
                for event in liquidity_events:
                    if event.start_age <= age <= event.end_age and event.taxable:
                        if event.recurrence == "One-time":
                            if age == event.start_age and event.amount > 0:
                                total_event_taxes += event.amount * (event.tax_rate / 100.0)
                        else:
                            if event.amount > 0:
                                event_amount = event.amount
                                if event.recurrence == "Monthly":
                                    event_amount *= 12
                                total_event_taxes += event_amount * (event.tax_rate / 100.0)
            
            st.markdown("#### Lifetime Tax Summary")
            tax_summary = {
                "Tax Category": [
                    "Withdrawal Taxes",
                    "Liquidity Event Taxes",
                    "Total Taxes Paid"
                ],
                "Amount": [
                    f"${total_withdrawal_taxes:,.2f}",
                    f"${total_event_taxes:,.2f}",
                    f"${timeline_a['taxes'].sum():,.2f}"
                ],
                "Percentage of Total": [
                    f"{(total_withdrawal_taxes / timeline_a['taxes'].sum() * 100) if timeline_a['taxes'].sum() > 0 else 0:.1f}%",
                    f"{(total_event_taxes / timeline_a['taxes'].sum() * 100) if timeline_a['taxes'].sum() > 0 else 0:.1f}%",
                    "100.0%"
                ]
            }
            st.dataframe(pd.DataFrame(tax_summary), hide_index=True, width="stretch")
        
        # Year-by-Year Calculation Logic
        with st.expander("Year-by-Year Calculation Details", expanded=True):
            st.markdown("#### Annual Calculation Formulas")
            st.markdown("""
            **For each year (age), the following calculations are performed:**
            
            1. **Start Balance** = Previous year's End Balance (or Current Balance for first year)
            
            2. **Contributions** = 
               - If age < retirement age: Contribution Amount × (12 if Monthly, else 1)
               - If age ≥ retirement age: $0
            
            3. **Liquidity Events** = Sum of all applicable events for this age:
               - **One-time events** (or Recurrence = "One-time"): Applied only at start_age
               - **Recurring events**: Applied every year from start_age to end_age
               - **Monthly recurring**: Amount × 12 (annualized)
               - **Negative amounts**: Treated as outflows/debts (subtracted from balance)
               - **Positive amounts**: Treated as inflows (added to balance)
            
            4. **Withdrawals** = 
               - If age < retirement age: $0
               - If "Fixed % of prior-year balance": 
                 * Base Amount = Prior Year End Balance × Withdrawal %
                 * If Monthly frequency: Annual Withdrawals = Base Amount × 12
                 * If Annual frequency: Annual Withdrawals = Base Amount
                 * (The % represents monthly or annual rate depending on frequency)
               - If "Fixed real dollars": 
                 * Base Amount = Withdrawal Amount × CPI Index (inflation-adjusted)
                 * If Monthly frequency: Annual Withdrawals = Base Amount × 12
                 * If Annual frequency: Annual Withdrawals = Base Amount
            
            5. **Fees** = Start Balance × Fee Rate
            
            6. **Taxes** = Tax Component A + Tax Component B
               - **Component A (Withdrawal Taxes)**: 
                 * If Withdrawal Tax Rate > 0: Withdrawals × Withdrawal Tax Rate
               - **Component B (Liquidity Event Taxes)**: 
                 * For each taxable liquidity event this year:
                 * If Taxable = True AND Amount > 0 (inflow):
                 * Event Tax = Event Amount × Event Tax Rate
                 * Total Event Taxes = Sum of all event taxes
               - **Note**: Only positive (inflow) events are taxed; outflows/debts are not taxed
            
            7. **Growth** = (Start Balance + Contributions + Liquidity - Withdrawals - Fees - Taxes) × Nominal Return Rate
            
            8. **End Balance (Nominal)** = Start Balance + Contributions + Liquidity - Withdrawals - Fees - Taxes + Growth
            
            9. **CPI Index** = Compounds annually by (1 + Inflation Rate)^(year - current_year)
            
            10. **End Balance (Real)** = End Balance (Nominal) / CPI Index
            """)
            
            st.markdown("#### Important: Withdrawal Frequency Behavior")
            st.markdown("""
            **How Withdrawal Frequency Works:**
            
            The **Withdrawal Frequency** setting (Annual vs Monthly) determines how to interpret your withdrawal percentage or amount:
            
            - **For "Fixed % of prior-year balance" method:**
              - **Annual**: The % is applied once per year
                - Example: 4% of $1M = $40,000/year
              - **Monthly**: The % represents a monthly rate, multiplied by 12
                - Example: 4% monthly × $1M × 12 months = $480,000/year
            
            - **For "Fixed real dollars" method:**
              - **Annual**: The amount is withdrawn once per year
                - Example: $50,000 = $50,000/year
              - **Monthly**: The amount is a monthly withdrawal, multiplied by 12
                - Example: $50,000/month × 12 months = $600,000/year
            
            ⚠️ **Note**: When using Monthly frequency with percentage withdrawals, the percentage is interpreted as a **monthly rate**. 
            A 4% monthly withdrawal rate equals 48% annually, which is typically unsustainable. For traditional retirement 
            planning (3-4% annual withdrawal rate), use **Annual** frequency.
            """)
            
            st.markdown("#### Sample Year Calculation (First 3 years)")
            sample_years = timeline_a.head(3).copy()
            
            for idx, row in sample_years.iterrows():
                st.markdown(f"**Age {int(row['age'])}:**")
                st.code(f"""
Start Balance:     ${row['start_balance_nominal']:>15,.2f}
+ Contributions:   ${row['contributions']:>15,.2f}
+ Liquidity Net:   ${row['liquidity_net']:>15,.2f}
- Withdrawals:     ${row['withdrawals']:>15,.2f}
- Fees:            ${row['fees']:>15,.2f}
- Taxes:           ${row['taxes']:>15,.2f}
+ Growth:          ${row['growth']:>15,.2f}
= End Balance:     ${row['end_balance_nominal']:>15,.2f}

CPI Index:         {row['cpi_index']:>18.4f}
Real End Balance:  ${row['end_balance_real']:>15,.2f}
                """, language="text")
        
        # Monte Carlo Details
        if enable_mc and mc_results_a:
            with st.expander("Monte Carlo Simulation Details", expanded=True):
                st.markdown("#### Simulation Methodology")
                st.markdown(f"""
                **Configuration:**
                - Number of Simulations: {scenario_a.mc_runs:,}
                - Random Seed: {MC_SEED} (for reproducibility)
                - Distribution: Normal(μ={scenario_a.nominal_return_pct}%, σ={scenario_a.return_stdev_pct}%)
                
                **Process:**
                1. For each simulation, generate {scenario_a.end_age - scenario_a.current_age + 1} random returns
                2. Each return follows: Return ~ Normal(μ, σ)
                3. Run the same timeline calculation with randomized returns
                4. Record final balance and whether portfolio stayed solvent
                
                **Results:**
                - Probability of Success: {mc_results_a['probability_no_shortfall']*100:.2f}% ({int(mc_results_a['probability_no_shortfall']*scenario_a.mc_runs):,} out of {scenario_a.mc_runs:,} simulations)
                - P10 Terminal Value: ${mc_results_a['p10_terminal']:,.2f} (10th percentile - worst 10%)
                - P50 Terminal Value: ${mc_results_a['median_terminal']:,.2f} (median outcome)
                - P90 Terminal Value: ${mc_results_a['p90_terminal']:,.2f} (90th percentile - best 10%)
                """)
        
        # Key Metrics Breakdown
        with st.expander("Key Metrics Calculation", expanded=True):
            st.markdown("#### Metric Definitions & Values")
            metrics_breakdown = {
                "Metric": [
                    "Terminal Value (Nominal)",
                    "Terminal Value (Real)",
                    "First Shortfall Age",
                    "Total Contributions",
                    "Total Withdrawals",
                    "Total Fees Paid",
                    "Total Taxes Paid",
                    "Total Growth",
                    "Net Liquidity Events"
                ],
                "Value": [
                    f"${metrics_a['terminal_nominal']:,.2f}",
                    f"${metrics_a['terminal_real']:,.2f}",
                    str(metrics_a['first_shortfall_age']) if metrics_a['first_shortfall_age'] else "None (Solvent)",
                    f"${timeline_a['contributions'].sum():,.2f}",
                    f"${timeline_a['withdrawals'].sum():,.2f}",
                    f"${timeline_a['fees'].sum():,.2f}",
                    f"${timeline_a['taxes'].sum():,.2f}",
                    f"${timeline_a['growth'].sum():,.2f}",
                    f"${timeline_a['liquidity_net'].sum():,.2f}"
                ],
                "Description": [
                    "Final portfolio balance in future dollars (not inflation-adjusted)",
                    "Final portfolio balance in today's purchasing power (inflation-adjusted)",
                    "First age where balance becomes negative (indicates insolvency)",
                    "Sum of all contributions made during accumulation phase",
                    "Sum of all withdrawals taken during retirement phase",
                    "Sum of all annual fees/expenses charged to portfolio",
                    "Sum of all taxes paid on withdrawals and taxable events",
                    "Sum of all investment returns earned over the planning horizon",
                    "Sum of all liquidity events (positive = net inflows, negative = net outflows)"
                ]
            }
            st.dataframe(pd.DataFrame(metrics_breakdown), hide_index=True, width="stretch")
        
        st.success("Calculation breakdown complete. All logic and formulas are documented above for manual verification.")


if __name__ == "__main__":
    main()
