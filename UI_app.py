# ui_display.py

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import threading
from datetime import datetime
from data_reader import (
    load_register_map, create_dataframe_from_registers, log_data,
    client_sunnal, read_register, write_to_modbus_slave,
    build_modbus_write_command, simulate
)
import mqtt_storage
from transform_data import handle_parameter_write
from new_mqtt_writer import handle_parameter_write_mqtt
from shared_state_UI import get_latest_data, is_topic_online, clear_latest_data
from mqtt_logic import start_streaming
from presets_config import presets_config

# ------------------ CACHED FUNCTIONS ------------------ #
@st.cache_data
def cached_load_register_map():
    return load_register_map()

@st.cache_data
def load_mqtt_topics():
    return [f"EZMCISAC{str(i).zfill(5)}" for i in range(1, 61)]

# ------------------ STREAMLIT CONFIG ------------------ #
st.set_page_config(page_title="Device Parameter Config", layout="wide")
st_autorefresh(interval=10000, limit=None, key="auto_refresh")

# ------------------ SIDEBAR - Protocol ------------------ #
st.sidebar.header("Protocol Selection")
protocol = st.sidebar.selectbox("Select Communication Protocol", ["MQTT", "Modbus"], index=0)

if protocol == "Select Protocol":
    st.warning("Please select a communication protocol from the sidebar.")
    st.stop()

# ------------------ MQTT Topic Selection ------------------ #
selected_topic = None
if protocol == "MQTT":
    # User selects a preset
    selected_preset = st.selectbox("Choose a Preset", ["None"] + list(presets_config.keys()))
    topics = load_mqtt_topics()
    if topics:
        selected_topic = st.sidebar.selectbox("Select MQTT Topic", topics, key="mqtt_topic")
        st.write(f"You selected topic: {selected_topic}")
        
        is_online_now = is_topic_online(f"/AC/1/{selected_topic}/Datalog")
        status = "🟢 Online" if is_online_now else "🔴 Offline"
        badge_color = "#d4edda" if is_online_now else "#f8d7da"
        text_color = "green" if is_online_now else "red"
        
        st.markdown(f"""
        <div style='background-color:{badge_color}; padding:8px 12px; margin-top:10px;
                    border-radius:6px; font-weight:bold; font-size:15px;
                    color:#000000; display:inline-block'>
            {selected_topic} is <span style='color:{text_color};'>{status}</span>
        </div>
        """, unsafe_allow_html=True)

        if 'last_topic' not in st.session_state:
            st.session_state.last_topic = None

        if selected_topic != st.session_state.last_topic:
            # Clear data on topic change (whether online or offline)
            clear_latest_data()  # 🧹 Always clear the external dictionary

            # Update the last selected topic
            st.session_state.last_topic = selected_topic

            # Start new data stream thread
            threading.Thread(target=start_streaming, args=(selected_topic,), daemon=True).start()
    else:
        st.sidebar.error("No MQTT topics found.")

elif protocol == "Modbus":
    com_port = st.sidebar.selectbox("Select COM Port", [f"COM{i}" for i in range(1, 8)], key="modbus_com_port")
    st.write(f"You selected {com_port} for Modbus communication.")

# ------------------ MAIN READ SECTION ------------------ #
st.header("📦 Live Parameters")

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

# Show Last Updated Time after df is defined
if protocol == "MQTT":
    is_online = is_topic_online(f"/AC/1/{selected_topic}/Datalog")
    if is_online and not df.empty and "Timestamp" in df["Name"].values:
        timestamp = df[df["Name"] == "Timestamp"]["Value"].iloc[-1]
    else:
        timestamp = "N/A"
elif protocol == "Modbus":
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

st.markdown(f"⏰ **Last updated:** {timestamp}")

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

if not df.empty:
    bitflag_df = df[df["Name"].isin(bitflag_items)]
    if not bitflag_df.empty:
        with col1:
            st.subheader("Fault and Alarm Codes")
            display_bitflags_side_by_side(bitflag_df.to_dict("records"))

    # Remove bitflag rows from df before splitting into table chunks
    non_bitflag_df = df[~df["Name"].isin(bitflag_items + ["Timestamp"])]

    # Chunk the remaining rows (non-bitflag) for table display
    chunk_size = 15
    table_chunks = [non_bitflag_df[i:i + chunk_size] for i in range(0, len(non_bitflag_df), chunk_size)]

    with col2:
        st.subheader("Live Inverter Parameters")

        if len(table_chunks) > 0:
            render_compact_table(table_chunks[0])

        # Add Inverter Comm Fault as bitflag-style
        inverter_fault_df = df[df["Name"] == "Inverter Comm Fault"]
        if not inverter_fault_df.empty:
            display_bitflags_side_by_side(inverter_fault_df.to_dict("records"))

    if protocol == "Modbus":
        log_data("discharge_register_log.csv", registers_perform, log_row)

    with col3:
        st.subheader('Live AC Parameters')

        # Define AC bitflag-like items and regular AC parameters
        ac_bitflags = ["AC Comm Fault"]
        ac_regular_params = ["AC Power_Status", "AC Set_temperature"]

        # Display regular AC parameters in table form
        ac_regular_df = df[df["Name"].isin(ac_regular_params)]
        if not ac_regular_df.empty:
            render_compact_table(ac_regular_df)

        # Display AC bitflags with color coding
        ac_bitflag_df = df[df["Name"].isin(ac_bitflags)]
        if not ac_bitflag_df.empty:
            display_bitflags_side_by_side(ac_bitflag_df.to_dict("records"))
else:
    st.info("📡 Waiting for live data from device...")

# ------------------ WRITE SECTION ------------------ #
st.markdown("---")
if protocol == "Modbus" and not df.empty:
    handle_parameter_write(
        df, client_sunnal, read_register,
        write_to_modbus_slave, build_modbus_write_command,
        create_dataframe_from_registers, simulate
    )
elif protocol == "MQTT" and not df.empty:
    if 'last_read_settings_topic' not in st.session_state:
        st.session_state.last_read_settings_topic = None
    
    if selected_topic != st.session_state.last_read_settings_topic:
        st.session_state.last_read_settings_topic = selected_topic
    
        # ✅ Clear old data when topic changes
        mqtt_storage.mqtt_storage_state['mqtt_response_data'].clear()
        mqtt_storage.mqtt_storage_state['structured_response_data'].clear()
        mqtt_storage.mqtt_storage_state['last_update_time'] = None

    handle_parameter_write_mqtt(selected_topic, selected_preset)
