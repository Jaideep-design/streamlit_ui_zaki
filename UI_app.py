# ui_display.py

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import threading

from data_reader import (
    load_register_map, create_dataframe_from_registers, log_data,
    client_sunnal, read_register, write_to_modbus_slave,
    build_modbus_write_command, simulate
)
from transform_data import handle_parameter_write
from mqtt_writer import handle_parameter_write_mqtt
from shared_state import get_latest_data
from mqtt_logic import start_streaming


# ------------------ CACHED FUNCTIONS ------------------ #
@st.cache_data
def cached_load_register_map():
    return load_register_map()

@st.cache_data
def load_mqtt_topics():
    try:
        df = pd.read_excel("mqtt_topics.xlsx")
        if 'Topics' in df.columns:
            return df['Topics'].dropna().tolist()
        return []
    except Exception:
        return []

# ------------------ BACKGROUND THREAD INIT ------------------ #
if 'mqtt_started' not in st.session_state:
    threading.Thread(target=start_streaming, daemon=True).start()
    st.session_state.mqtt_started = True

# ------------------ STREAMLIT CONFIG ------------------ #
st.set_page_config(page_title="Device Parameter Config", layout="wide")
st_autorefresh(interval=30000, limit=None, key="auto_refresh")

# ------------------ SIDEBAR - Protocol ------------------ #
st.sidebar.header("Protocol Selection")
protocol = st.sidebar.selectbox("Select Communication Protocol", ["Select Protocol", "Modbus", "MQTT"])

if protocol == "Select Protocol":
    st.warning("Please select a communication protocol from the sidebar.")
    st.stop()

# MQTT topic selection
selected_topic = None
if protocol == "MQTT":
    topics = load_mqtt_topics()
    if topics:
        selected_topic = st.sidebar.selectbox("Select MQTT Topic", topics)
        st.write(f"You selected topic: {selected_topic}")
    else:
        st.sidebar.error("No MQTT topics found in the Excel file or failed to load.")

elif protocol == "Modbus":
    com_port = st.sidebar.selectbox("Select COM Port", [f"COM{i}" for i in range(1, 8)])
    st.write(f"You selected {com_port} for Modbus communication.")

# ------------------ MAIN READ SECTION ------------------ #
st.header("📦 Inverter Read Registers")

registers_perform = cached_load_register_map()
if not registers_perform:
    st.info("No register definitions found in `register_map.json`.")
    st.stop()

df_modbus, bitflag_items, log_row = create_dataframe_from_registers(registers_perform)

# Use MQTT or Modbus
if protocol == "MQTT":
    mqtt_data = get_latest_data()
    if mqtt_data:
        df_mqtt = pd.DataFrame([mqtt_data])
        df = df_mqtt.melt(var_name='Name', value_name='Value')
    else:
        st.warning("⚠️ No MQTT data received yet.")
        df = pd.DataFrame()
else:
    df = df_modbus

# ------------------ DISPLAY DATA ------------------ #
col1, col2, col3 = st.columns(3)

def display_bitflags_side_by_side(bitflag_rows):
    for i in range(0, len(bitflag_rows), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(bitflag_rows):
                entry = bitflag_rows[i + j]
                name = entry["Name"]
                value = entry["Value"]
                color = "#d4edda" if value == 0 else "#f8d7da"
                with cols[j]:
                    st.markdown(
                        f"<div style='background-color:{color}; "
                        f"margin:4px 0; padding:6px 10px; "
                        f"font-weight:bold; border-radius:4px; "
                        f"color:#000000; font-size:13px;'>{name}</div>",
                        unsafe_allow_html=True
                    )

def render_compact_table(df):
    table_html = "<style>th, td { padding: 2px 6px !important; font-size: 15px !important; }</style>"
    table_html += df.to_html(index=False, escape=False)
    st.markdown(table_html, unsafe_allow_html=True)

bitflag_df = df[df["Name"].isin(bitflag_items)]
if not bitflag_df.empty:
    with col1:
        display_bitflags_side_by_side(bitflag_df.to_dict("records"))

chunk_size = 14
table_chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

with col2:
    st.subheader(f"{protocol} Parameters - 1")
    if len(table_chunks) > 0:
        render_compact_table(table_chunks[0])

with col3:
    st.subheader(f"{protocol} Parameters - 2")
    if len(table_chunks) > 1:
        render_compact_table(table_chunks[1])

# Timestamp footer and logging
if "Timestamp" in df["Name"].values:
    timestamp = df[df["Name"] == "Timestamp"]["Value"].iloc[-1]
    st.caption(f"⏰ Last updated: {timestamp}")

if protocol == "Modbus":
    log_data("discharge_register_log.csv", registers_perform, log_row)

# ------------------ WRITE SECTION ------------------ #
st.markdown("---")
if protocol == "Modbus" and not df.empty:
    handle_parameter_write(
        df, client_sunnal, read_register,
        write_to_modbus_slave, build_modbus_write_command,
        create_dataframe_from_registers, simulate
    )
elif protocol == "MQTT" and not df.empty:
    handle_parameter_write_mqtt(df)
