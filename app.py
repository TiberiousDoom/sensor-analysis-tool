import streamlit as st

st.set_page_config(page_title="Sensor Analysis Tool", layout="wide")
st.title("🔧 Sensor Data Analysis Tool")

st.write("If you can see this message, the app is working!")
st.write("Dependencies are loaded correctly.")

# Test imports
try:
    import pandas as pd
    st.success("✅ Pandas imported successfully")
except Exception as e:
    st.error(f"❌ Pandas error: {e}")

try:
    import plotly.graph_objects as go
    st.success("✅ Plotly imported successfully")
except Exception as e:
    st.error(f"❌ Plotly error: {e}")

try:
    import numpy as np
    st.success("✅ NumPy imported successfully")
except Exception as e:
    st.error(f"❌ NumPy error: {e}")

st.info("All basic imports working! Ready to add functionality.")
