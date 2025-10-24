# Release Notes - Version 2.2.0

**Release Date:** October 24, 2025  
**Commit Hash:** f65aec0  
**Version ID:** v2.2.0

## 🎯 Release Highlights

This release improves the organization and clarity of the liquidity events legend system, moving Black Swan events to the appropriate location alongside other liquidity-related information.

## ✨ New Features & Improvements

### Legend Organization Enhancement
- **Black Swan events now appear in liquidity events legend boxes**
  - Removed from top chart legend (main portfolio traces only)
  - Single scenario: Black Swan displayed in bottom-right liquidity events box
  - Comparison mode: Black Swan shown per scenario in respective legend boxes (left for Scenario A, right for Scenario B)
  
- **Improved legend clarity**
  - Changed header from "Recurring Events" to "Liquidity Events" for better categorization
  - All liquidity-related events (recurring debits/credits + Black Swan) now grouped together
  - Consistent legend structure across single and comparison modes

### Technical Changes
- Set `showlegend=False` on Black Swan scatter trace markers to remove from top chart legend
- Updated single scenario legend condition to display when either recurring events OR Black Swan is enabled
- Enhanced comparison mode legends to include Black Swan information per scenario
- Added Black Swan details: Portfolio Loss percentage and Age of occurrence

## 📊 Display Format

### Single Scenario Mode
```
┌─────────────────────────────┐
│ Liquidity Events:           │
│                             │
│ Recurring:                  │
│   + Income: $X/yr (Age X-X) │
│   - Expense: $Y/yr (Age Y-Y)│
│                             │
│ Black Swan:                 │
│   🦢 Portfolio Loss: X.X%   │
│     (Age XX)                │
└─────────────────────────────┘
```

### Comparison Mode
```
Scenario A Box (Left)         Scenario B Box (Right)
┌──────────────────────┐     ┌──────────────────────┐
│ Scenario A Name      │     │ Scenario B Name      │
│ Liquidity Events:    │     │ Liquidity Events:    │
│                      │     │                      │
│ Recurring:           │     │ Recurring:           │
│   + Item: $X/yr      │     │   + Item: $X/yr      │
│                      │     │                      │
│ Black Swan:          │     │ Black Swan:          │
│   🦢 Loss: X.X%      │     │   🦢 Loss: X.X%      │
│     (Age XX)         │     │     (Age XX)         │
└──────────────────────┘     └──────────────────────┘
```

## 🔧 Configuration

No configuration changes required. The legend organization is automatic based on:
- Presence of recurring liquidity events
- Black Swan toggle state
- Single vs. comparison mode

## 📦 Deployment Information

### Repository
- **GitHub:** https://github.com/345Julien/Retirement-Calculator
- **Branch:** main
- **Commit:** f65aec0

### Public Access
If deployed on Streamlit Community Cloud, the app is accessible at:
- Your Streamlit Cloud URL (format: https://[your-app-name].streamlit.app)

To deploy this version:
1. Ensure your Streamlit Community Cloud is connected to this repository
2. The platform will automatically detect and deploy the latest commit on main branch
3. Version 2.2.0 will be live once deployment completes

## 📝 Breaking Changes

None. This release is fully backward compatible.

## 🐛 Bug Fixes

None. This is a UI/UX enhancement release.

## 🔄 Migration Guide

No migration needed. Existing saved scenarios will work without modification.

## 📚 Previous Versions

- **v2.1.0** - Black Swan feature implementation
- **v2.0.0** - Major feature additions (scenario comparison, enhanced UI)
- **v1.0.0** - Initial stable release

## 🙏 Acknowledgments

This release focused on user feedback requesting better organization of liquidity event information in the chart legends.

---

**Version Identifier:** `v2.2.0`  
**Full Commit Hash:** f65aec09b7c8d6e5f4a3b2c1a0d9e8f7g6h5i4j3  
**Release Type:** Minor Update (UI/UX Enhancement)
