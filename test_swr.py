#!/usr/bin/env python3
"""
Independent verification of Safe Withdrawal Rate calculation.
Tests whether the app's SWR calculation is correct.
"""

def simulate_portfolio(
    initial_balance: float,
    years: int,
    withdrawal_rate: float,  # as decimal (e.g., 0.04 for 4%)
    return_rate: float,  # as decimal (e.g., 0.07 for 7%)
    fee_rate: float = 0.0,
    inflation_rate: float = 0.0
) -> tuple[float, float]:
    """
    Simulate portfolio balance over time with percentage-based withdrawals.
    Returns (final_balance, minimum_balance)
    """
    balance = initial_balance
    min_balance = balance
    prior_year_balance = balance
    
    for year in range(years):
        # Start balance
        start_balance = balance
        
        # Withdrawal based on prior year's ending balance
        withdrawal = prior_year_balance * withdrawal_rate
        
        # Fees
        fees = start_balance * fee_rate
        
        # Balance after withdrawals and fees
        balance_after_cashflows = start_balance - withdrawal - fees
        
        # Growth
        growth = balance_after_cashflows * return_rate
        
        # End balance
        balance = balance_after_cashflows + growth
        
        # Track minimum
        if balance < min_balance:
            min_balance = balance
        
        # Update prior year balance for next iteration
        prior_year_balance = balance
        
        print(f"Year {year+1}: Start=${start_balance:,.0f}, Withdrawal=${withdrawal:,.0f}, "
              f"Growth=${growth:,.0f}, End=${balance:,.0f}")
    
    return balance, min_balance


def find_safe_withdrawal_rate(
    initial_balance: float,
    years: int,
    return_rate: float,
    fee_rate: float = 0.0,
    tolerance: float = 0.0001,
    max_iterations: int = 50
) -> float:
    """
    Binary search to find maximum withdrawal rate where balance never goes negative.
    Returns safe withdrawal rate as decimal (e.g., 0.0399 for 3.99%).
    """
    low, high = 0.0, 0.20  # Search between 0% and 20%
    best_rate = 0.0
    
    print(f"\n=== Finding Safe Withdrawal Rate ===")
    print(f"Parameters: Balance=${initial_balance:,.0f}, Years={years}, Return={return_rate*100:.1f}%, Fee={fee_rate*100:.2f}%")
    print(f"\nBinary Search Iterations:")
    
    for iteration in range(max_iterations):
        mid = (low + high) / 2.0
        
        # Test this withdrawal rate
        final_balance, min_balance = simulate_portfolio(
            initial_balance, years, mid, return_rate, fee_rate
        )
        
        if min_balance >= 0:
            # Success, try higher
            best_rate = mid
            low = mid
            result = "✓ SOLVENT"
        else:
            # Failed, try lower
            high = mid
            result = "✗ NEGATIVE"
        
        print(f"Iter {iteration+1}: Rate={mid*100:.4f}% → Min Balance=${min_balance:,.0f} {result}")
        
        if high - low < tolerance:
            break
    
    print(f"\n=== RESULT: Safe Withdrawal Rate = {best_rate*100:.4f}% ===\n")
    return best_rate


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEST 1: Simple case - Already retired, 30 years, 7% return, no fees")
    print("="*80)
    
    swr = find_safe_withdrawal_rate(
        initial_balance=1_000_000,
        years=30,
        return_rate=0.07,
        fee_rate=0.0
    )
    
    print("\n" + "="*80)
    print("TEST 2: With fees - 7% return, 0.5% annual fees")
    print("="*80)
    
    swr = find_safe_withdrawal_rate(
        initial_balance=1_000_000,
        years=30,
        return_rate=0.07,
        fee_rate=0.005
    )
    
    print("\n" + "="*80)
    print("TEST 3: Default app parameters simulation")
    print("Age 30-95 (65 years), but contributions stop at 65")
    print("This is complex - contributions for 35 years, then withdrawals for 30 years")
    print("="*80)
    
    # For this we need to simulate the accumulation phase first
    # Starting balance: $100,000
    # Contributions: $500/month = $6,000/year for 35 years
    # Then retirement withdrawals for 30 years
    
    balance = 100_000
    contribution = 6_000
    return_rate = 0.07
    fee_rate = 0.005
    
    print("\nACCUMULATION PHASE (Age 30-64, 35 years):")
    for year in range(35):
        age = 30 + year
        start_balance = balance
        fees = start_balance * fee_rate
        balance_after_cashflows = start_balance + contribution - fees
        growth = balance_after_cashflows * return_rate
        balance = balance_after_cashflows + growth
        
        if year == 0 or year == 34 or year % 10 == 9:
            print(f"Age {age}: Start=${start_balance:,.0f}, Contrib=${contribution:,.0f}, "
                  f"Growth=${growth:,.0f}, End=${balance:,.0f}")
    
    print(f"\nBalance at retirement (age 65): ${balance:,.0f}")
    
    # Now find SWR for retirement phase
    print("\nRETIREMENT PHASE (Age 65-95, 30 years):")
    swr = find_safe_withdrawal_rate(
        initial_balance=balance,
        years=30,
        return_rate=0.07,
        fee_rate=0.005
    )
