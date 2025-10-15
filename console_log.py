import streamlit as st
from streamlit.components.v1 import html

def log_to_browser_console(message):

    js_code = f"""
    <script>
        console.log("STREAMLIT LOG: {message}");
    </script>
    """
    html(js_code, height=0, width=0)

# ---------------------------------------------------