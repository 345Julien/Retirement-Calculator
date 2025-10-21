# Contributing to Harbor Stone Retirement Calculator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

---

## 🌟 Ways to Contribute

- **Report bugs**: Submit detailed bug reports via GitHub Issues
- **Suggest features**: Propose new features or enhancements
- **Improve documentation**: Fix typos, clarify instructions, add examples
- **Submit code**: Fix bugs or implement new features
- **Test**: Run the app and report any issues or edge cases
- **Share**: Star the repo and share with others who might benefit

---

## 🐛 Reporting Bugs

### Before Submitting
1. Check if the bug has already been reported in Issues
2. Verify you're using the latest version
3. Try to reproduce the bug with minimal configuration

### Bug Report Template
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. Enter value '...'
4. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., macOS 14.0]
- Python Version: [e.g., 3.12]
- Streamlit Version: [e.g., 1.28.0]

**Additional context**
Any other relevant information.
```

---

## 💡 Suggesting Features

### Feature Request Template
```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Use case**
Who would benefit and how would they use this feature?

**Additional context**
Mockups, examples, or other information.
```

---

## 🔨 Development Setup

### 1. Fork and Clone
```bash
# Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/retirement-calculator.git
cd retirement-calculator
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

---

## 📝 Code Style Guide

### Python Style
- Follow **PEP 8** guidelines
- Use **type hints** for function parameters and return values
- Add **docstrings** to all functions (Google style)
- Keep functions **focused** and **testable**
- Use **descriptive variable names**

### Example Function
```python
def calculate_withdrawal(
    balance: float,
    rate: float,
    frequency: str
) -> float:
    """
    Calculate annual withdrawal amount.
    
    Args:
        balance: Portfolio balance in dollars
        rate: Withdrawal rate as decimal (e.g., 0.04 for 4%)
        frequency: 'Annual' or 'Monthly'
    
    Returns:
        Annual withdrawal amount in dollars
    
    Example:
        >>> calculate_withdrawal(1000000, 0.04, 'Annual')
        40000.0
    """
    annual_amount = balance * rate
    if frequency == "Monthly":
        annual_amount *= 12
    return annual_amount
```

### Code Organization
- **Constants** at top of file (UPPERCASE_WITH_UNDERSCORES)
- **Dataclasses** next
- **Pure functions** (calculations) before UI code
- **UI functions** last
- **main()** at bottom

### Comments
- Use comments to explain **why**, not **what**
- Avoid obvious comments
- Update comments when changing code
- Remove commented-out code before committing

---

## 🧪 Testing Guidelines

### Manual Testing Checklist
- [ ] App launches without errors
- [ ] All inputs accept valid values
- [ ] Charts render correctly
- [ ] Liquidity events work as expected
- [ ] Monte Carlo simulation runs
- [ ] Scenarios save and load
- [ ] Export functions work
- [ ] No console errors or warnings

### Test New Features
When adding a feature:
1. Test with typical values
2. Test with edge cases (zero, negative, very large)
3. Test with empty data
4. Test error handling
5. Verify UI updates correctly

### Regression Testing
After bug fixes:
1. Verify fix resolves the issue
2. Check that existing features still work
3. Test related functionality
4. Look for similar bugs elsewhere

---

## 📤 Submitting Changes

### 1. Commit Your Changes
```bash
# Make your changes
git add .

# Commit with descriptive message
git commit -m "Add feature: Safe withdrawal rate calculator"
```

### Commit Message Format
```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, missing semicolons, etc.)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat: Add tax rate reference guide

Add collapsible sidebar section with tax rates for common jurisdictions.
Includes examples from tax havens to high-tax countries.

fix: Resolve NameError in build_timeline function

Removed embedded Streamlit UI code from pure computation function.
All variables now assigned correctly on every loop iteration.

Fixes #42
```

### 2. Push to Your Fork
```bash
git push origin feature/your-feature-name
```

### 3. Create Pull Request
1. Go to the original repository on GitHub
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill out the PR template
5. Submit for review

### Pull Request Template
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran and how to reproduce.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have tested with edge cases
- [ ] Any dependent changes have been merged

## Screenshots (if applicable)
Add screenshots for UI changes.
```

---

## 🔍 Code Review Process

### What We Look For
- **Correctness**: Does it work as intended?
- **Code Quality**: Is it readable and maintainable?
- **Testing**: Has it been adequately tested?
- **Documentation**: Are changes documented?
- **Style**: Does it follow guidelines?
- **Performance**: Is it efficient?

### Review Timeline
- Initial response: Within 3 days
- Full review: Within 1 week
- Feedback: We'll provide constructive suggestions

### After Review
- Address feedback promptly
- Push changes to same branch
- PR will be re-reviewed
- Once approved, we'll merge

---

## 🎯 Development Priorities

### High Priority
- Bug fixes (especially those affecting calculations)
- Security issues
- Documentation improvements
- Performance optimizations

### Medium Priority
- New features from roadmap
- UI/UX enhancements
- Additional test coverage

### Low Priority
- Code refactoring (without functional changes)
- Minor style improvements
- Nice-to-have features

---

## 📚 Resources

### Project Documentation
- [README.md](README.md) - Project overview
- [QUICK_START.md](QUICK_START.md) - User guide
- [TEST_RESULTS.md](TEST_RESULTS.md) - Test reports
- [CHANGELOG.md](CHANGELOG.md) - Version history

### External Resources
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python Documentation](https://plotly.com/python/)
- [pandas Documentation](https://pandas.pydata.org/docs/)
- [PEP 8 Style Guide](https://pep8.org/)

---

## 💬 Communication

### Questions?
- Open a GitHub Discussion for general questions
- Open an Issue for bugs or feature requests
- Comment on relevant PRs or Issues

### Be Respectful
- Use welcoming and inclusive language
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🙏 Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort!

---

**Questions?** Feel free to open an issue or discussion. We're here to help!
