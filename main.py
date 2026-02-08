import streamlit as st
import os
import time

st.set_page_config(page_title="Loading Sign Shop Suite...")

st.markdown("""
<meta http-equiv="refresh" content="4">
<script>setTimeout(function(){window.location.reload(true)},4000)</script>
<div style="display:flex;align-items:center;justify-content:center;height:80vh;background:#0a0a0a;color:#e5e5e5;font-family:Inter,sans-serif">
<div style="text-align:center">
<div style="font-size:32px;font-weight:700;color:#39FF14">KB <span style="color:#e5e5e5;font-size:18px;letter-spacing:2px">SIGNS</span></div>
<div style="margin-top:16px;color:#999">Loading Sign Shop Suite...</div>
</div>
</div>
""", unsafe_allow_html=True)

time.sleep(0.3)

os.execvp("npx", ["npx", "tsx", "server/index.ts"])
