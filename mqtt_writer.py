# Add this inside ui_display.py or a new file like mqtt_writer.py

import paho.mqtt.client as mqtt
import streamlit as st
import json
import pandas as pd
from shared_state import latest_data, latest_data_lock  # For updating shared state
from data_reader import create_dataframe_from_mqtt


def handle_parameter_write_mqtt(df, simulate):
    st.subheader("✍️ Write Parameters to Inverter (MQTT)")
    # MQTT connection details
    MQTT_BROKER = "ecozen.ai"
    MQTT_PORT = 1883
    MQTT_TOPIC = "/AC/1/EZMCISAC00001/Command"
    
    try:
        with open('output.json', 'r') as f:
            register_data = json.load(f)
            registers = register_data.get("registers", [])
    except Exception as e:
        st.error(f"Failed to load parameter config: {e}")
        registers = []

    if not registers:
        st.info("No write parameters defined in output.json")
        return
    
    st.header("⚙️ Inverter Write Parameters")
    header_cols = st.columns([1, 1, 1, 1])
    with header_cols[0]: st.markdown("**Parameter**")
    with header_cols[1]: st.markdown("**Current Value**")
    with header_cols[2]: st.markdown("**New Value to be Set**")
    with header_cols[3]: st.markdown("**Allowable Range (Simulated)**")

    st.markdown("---")
    
    new_df, log_row = create_dataframe_from_mqtt(registers, latest_data)
    # Append the new dataframe to the existing one
    if df is not None and not df.empty:
        df = pd.concat([df, new_df], ignore_index=True)
    else:
        df = new_df
        
    for idx, reg in enumerate(registers):
        # Define single-line compact layout
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 0.5, 1])  # Name, Current, Input, Set, Range

        with col1:
            st.markdown(f"**{reg['name']}**")

        with col2:
            current_row = df[df['Name'] == reg['name']]
            if not current_row.empty:
                val = current_row.iloc[0]["Value"]
                st.code(str(val))
            else:
                st.code("N/A")
        
        # Initialize button state and value holder
        set_btn = False
        selected_command = None
        write_val = None

        if "commands" in reg:
            with col3:
                selected_command = st.selectbox(
                    " ", list(reg["commands"].keys()), key=f"cmd_{reg['name']}"
                )
            with col4:
                st.write("")
                set_btn = st.button("Set", key=f"set_{idx}")
        else:
            with col3:
                write_val = st.number_input(
                    " ",
                    key=f"input_{idx}",
                    value=reg["range"][0] if "range" in reg else 0,
                    min_value=reg["range"][0] if "range" in reg else None,
                    max_value=reg["range"][1] if "range" in reg else None,
                    format="%d"
                )
            with col4:
                st.write("")
                set_btn = st.button("Set", key=f"set_{idx}")

        with col5:
            if "description" in reg:
                st.caption(f"Options: {reg['description']}")
            elif "range" in reg:
                st.markdown(f"{reg['range'][0]} to {reg['range'][1]}")
            else:
                st.markdown(" ")
        
        # Execute Set button
        if set_btn:
            reg_address = reg.get("write_address")
        
            if "commands" in reg:
                hex_string = reg["commands"][selected_command]
                hex_bytes = bytes.fromhex(hex_string.replace(" ", ""))
        
                if simulate:
                    st.success(f"✅ (Simulated) `{reg['name']}` command `{selected_command}` selected")
                    st.code(hex_string, language="text")
                    df.loc[df["Name"] == reg["name"], "Value"] = selected_command
                else:
                    try:
                        # Extract register and value from command hex string
                        # hex_string format: "05 06 13 99 00 03 1C E4"
                        # Register = bytes 2-3 => 13 99 => 0x1399 = 5017
                        # Value = bytes 4-5 => 00 03 => 0x0003 = 3
        
                        hex_clean = hex_string.replace(" ", "")
                        register_hex = hex_clean[4:8]  # 13 99
                        value_hex = hex_clean[8:12]    # 00 03
        
                        reg_addr = int(register_hex, 16)
                        value = int(value_hex, 16)
        
                        # Format as required: UP#,0001:00003
                        mqtt_message = f"UP#,{reg_addr:04}:{value:05}"
        
                        mqtt_client = mqtt.Client()
                        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                        mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                        mqtt_client.disconnect()
        
                        st.success(f"✅ `{reg['name']}` command `{selected_command}` sent via MQTT")
                        st.code(mqtt_message, language="text")
        
                        with latest_data_lock:
                            latest_data[reg["name"]] = selected_command
        
                        df.loc[df["Name"] == reg["name"], "Value"] = selected_command
                    except Exception as e:
                        st.error(f"⚠️ Error sending MQTT command: {e}")
        
            else:
                try:
                    # Format as: UP#,<register>:<value>
                    mqtt_message = f"UP#,{int(reg_address):04}:{int(write_val):05}"
        
                    if simulate:
                        st.success(f"✅ (Simulated) `{reg['name']}` written with value `{write_val}`")
                        st.code(mqtt_message, language="text")
                    else:
                        mqtt_client = mqtt.Client()
                        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                        mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                        mqtt_client.disconnect()
        
                        st.success(f"✅ `{reg['name']}` written with value `{write_val}` via MQTT")
                        st.code(mqtt_message, language="text")
        
                    with latest_data_lock:
                        latest_data[reg["name"]] = write_val
        
                    df.loc[df["Name"] == reg_address, "Value"] = write_val
                except Exception as e:
                    st.error(f"⚠️ Error writing to MQTT: {e}")


