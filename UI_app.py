# ui_display.py

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from data_reader import (
    load_register_map, create_dataframe_from_registers, log_data,
    client_sunnal, read_register, write_to_modbus_slave,
    build_modbus_write_command, simulate
)
from transform_data import handle_parameter_write
from mqtt_writer import handle_parameter_write_mqtt
from shared_state import get_latest_data
from mqtt_logic import start_streaming
import threading

# Start MQTT or dummy stream in background
mqtt_thread = threading.Thread(target=start_streaming, daemon=True)
mqtt_thread.start()

# Streamlit config
st.set_page_config(page_title="Device Parameter Config", layout="wide")
st_autorefresh(interval=60000, limit=None, key="auto_refresh")

# ------------------ PROTOCOL SELECTION ------------------ #
st.sidebar.header("Protocol Selection")
protocol = st.sidebar.selectbox("Select Communication Protocol", ["Select Protocol", "Modbus", "MQTT"])

if protocol == "Select Protocol":
    st.warning("Please select a communication protocol from the sidebar.")
    st.stop()

# ------------------ READ PARAMETER SECTION ------------------ #
st.header("\U0001F4E6 Inverter Read registers")

registers_perform = load_register_map()
df_modbus, df_mqtt = None, None

# def display_bitflag_box(name, value):
#     color = "#d4edda" if value == 0 else "#f8d7da"  # Green for 0, Red for 1
#     st.markdown(
#         f"<div style='background-color:{color}; "
#         f"margin:1px 0; padding:2px 6px; "
#         f"font-weight:bold; border-radius:2px; "
#         f"color:#000000; font-size:12px;'>{name}</div>",
#         unsafe_allow_html=True
#     )

# def display_bitflags_side_by_side(bitflag_rows):
#     for i in range(0, len(bitflag_rows), 2):
#         with st.container():
#             cols = st.columns(2)
#             for j in range(2):
#                 if i + j < len(bitflag_rows):
#                     row = bitflag_rows[i + j]
#                     with cols[j]:
#                         display_bitflag_box(row["Name"], row["Value"])
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
                        f"color:#000000; font-size:13px;'>"
                        f"{name}</div>",
                        unsafe_allow_html=True
                    )


def render_compact_table(df):
    table_html = "<style>th, td { padding: 2px 6px !important; font-size: 15px !important; }</style>"
    table_html += df.to_html(index=False, escape=False)
    st.markdown(table_html, unsafe_allow_html=True)

if registers_perform:
    df_modbus, bitflag_items, log_row = create_dataframe_from_registers(registers_perform)

    # ------------ Handle MQTT protocol ------------ #
    if protocol == "Modbus":
        df = df_modbus
    elif protocol == "MQTT":
        st.subheader("📶 Real-time MQTT Data")
    
        mqtt_data = get_latest_data()
    
        if mqtt_data:
            df_mqtt = pd.DataFrame([mqtt_data])
            reshaped_df = df_mqtt.melt(var_name='Name', value_name='Value')
            df = reshaped_df
        else:
            st.warning("⚠️ No MQTT data received yet.")
            df = pd.DataFrame()

    col1, col2, col3 = st.columns(3)

    # Filter and display only bitflag-related rows
    bitflag_df = df[df["Name"].isin(bitflag_items)]
    
    if not bitflag_df.empty:
        with col1:
            display_bitflags_side_by_side(bitflag_df.to_dict("records"))

    chunk_size = 14
    table_chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

    with col2:
        st.subheader(f"{protocol} Parameters - 1")
        if len(table_chunks) > 0:
            df1 = pd.DataFrame(table_chunks[0])
            render_compact_table(df1)

    with col3:
        st.subheader(f"{protocol} Parameters - 2")
        if len(table_chunks) > 1:
            df2 = pd.DataFrame(table_chunks[1])
            render_compact_table(df2)

    if protocol == "Modbus":
        timestamp_rows = df[df["Name"] == "Timestamp"]
        if not timestamp_rows.empty:
            latest_timestamp = timestamp_rows["Value"].iloc[-1]
            st.caption(f"\U0001F551 Last updated: {latest_timestamp}")
        log_file = "discharge_register_log.csv"
        log_data(log_file, registers_perform, log_row)
        
    if protocol == "MQTT" and "Timestamp" in df.columns:
        latest_timestamp = df["Timestamp"].iloc[-1]
        st.caption(f"\U0001F551 Last updated: {latest_timestamp}")


else:
    st.info("No register definitions found in `register_map.json`.")

# ------------------ WRITE PARAMETER SECTION ------------------ #
st.markdown("---")

if protocol == "Modbus" and not df.empty:
    handle_parameter_write(
        df, client_sunnal, read_register,
        write_to_modbus_slave, build_modbus_write_command,
        create_dataframe_from_registers, simulate
    )

elif protocol == "MQTT" and not df.empty:
    handle_parameter_write_mqtt(df, simulate)
