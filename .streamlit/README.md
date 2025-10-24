# Streamlit Community Cloud Deployment

This app is deployed on Streamlit Community Cloud.

## Deployment Configuration

- **Python Version**: 3.9+
- **Main File**: `app.py`
- **Branch**: `main`
- **Auto-deploy**: Enabled (deploys on push to main)

## Environment

The app uses the following dependencies (see `requirements.txt`):
- streamlit>=1.28.0
- plotly>=5.17.0
- numpy>=1.24.0
- pandas>=2.0.0

## Configuration

Theme and server settings are configured in `.streamlit/config.toml`

## Local Development

To run locally:
```bash
streamlit run app.py
```

## Public URL

Once deployed, the app will be available at:
`https://[your-app-name].streamlit.app`
