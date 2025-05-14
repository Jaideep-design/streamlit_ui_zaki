# -*- coding: utf-8 -*-
"""
Created on Fri May  9 17:28:35 2025

@author: Admin
"""

import paho.mqtt.client as mqtt
import streamlit as st
import time
import json
import re
from data_reader import create_dataframe_from_mqtt
from presets_config import presets_config
import threading
import mqtt_storage
from datetime import datetime


# Placeholder to collect incoming response data
response_received = threading.Event()

def on_message_response(client, userdata, msg):
    try:
        raw_message = msg.payload.decode()
        match = re.search(r'"msgId"\s*:\s*"([^"]+)"\s*,\s*"rsp"\s*:\s*"(.+)"\s*}', raw_message, re.DOTALL)
        if not match:
            print("Payload format not recognized.")
            return

        msg_id = match.group(1)
        rsp_raw = match.group(2).replace('\r', '').replace('\n', '\\n').strip()

        try:
            rsp_raw = rsp_raw.encode().decode('unicode_escape')
        except Exception as decode_err:
            print(f"Unicode decode failed: {decode_err}")
            return

        if rsp_raw.strip() == "READ PROCESSING":
            print("Received intermediate status message. Waiting for data...")
            return

        rsp_lines = rsp_raw.strip().splitlines()
        if not rsp_lines:
            print("No response lines found.")
            return

        header = rsp_lines[0]
        data_lines = rsp_lines[1:]

        rsp_data_dict = {}
        for line in data_lines:
            line = line.strip()
            if ":" in line:
                reg, val = line.split(":", 1)
                reg = reg.strip()
                val = val.strip()
                try:
                    rsp_data_dict[reg] = int(val)
                except ValueError:
                    print(f"Non-integer value for {reg}: {val}")
            else:
                print(f"Ignored malformed line: {line}")

        structured_json = {
            "msgId": msg_id,
            "rsp": {
                "header": header,
                "data": rsp_data_dict
            }
        }

        mqtt_storage.mqtt_storage_state['mqtt_response_data'].update(rsp_data_dict)
        mqtt_storage.mqtt_storage_state["last_update_time"] = datetime.now()  # ✅ SET IT HERE

        mqtt_storage.mqtt_storage_state['structured_response_data'].clear()
        mqtt_storage.mqtt_storage_state['structured_response_data'].update(structured_json)

        print("Parsed response data:", rsp_data_dict)
        response_received.set()

    except Exception as e:
        print(f"Failed to parse MQTT message: {e}")


def handle_parameter_write_mqtt(selected_topic, selected_preset=None):
    st.subheader("✍️ Inverter Settings")

    MQTT_BROKER = "ecozen.ai"
    MQTT_PORT = 1883
    MQTT_TOPIC = f"/AC/1/{selected_topic}/Command"

    try:
        with open('new_outputs.json', 'r') as f:
            register_data = json.load(f)
            registers = register_data.get("registers", [])
    except Exception as e:
        st.error(f"Failed to load parameter config: {e}")
        return

    if not registers:
        st.info("No write parameters defined in output.json")
        return
   
    # Identify registers with same read & write addresses
    same_read_write_regs = {
        str(reg["read_address"]): reg["name"]
        for reg in registers
        if "read_address" in reg and "write_address" in reg and reg["read_address"] == reg["write_address"]
    }
    
    # Collect read addresses for registers NOT having same read/write
    read_registers = [
        str(reg["read_address"])
        for reg in registers
        if "read_address" in reg and not (
            "write_address" in reg and reg["read_address"] == reg["write_address"]
        )
    ]
    
    # Add the rest (same read/write) to be read but handled differently
    read_registers += list(same_read_write_regs.keys())
    
    # Construct the READ message
    read_command = f"READ**12345##1234567890,{','.join(read_registers)}"
    
    # Triggered by button
    if st.button("🔄 Read All Setting Parameters"):
        # MQTT setup
        command_client = mqtt.Client()
        command_client.on_message = on_message_response
        command_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
        # Subscribe to response topic
        subscribe_topic = f"/AC/1/{selected_topic}/Response"
        command_client.subscribe(subscribe_topic)
        command_client.loop_start()
    
        # Publish the command
        publish_topic = f"/AC/1/{selected_topic}/Command"
        response_received.clear()
        command_client.publish(publish_topic, read_command)
    
        if response_received.wait(timeout=15):
            st.success("✅ Response received from inverter.")
    
        else:
            st.error("❌ Timeout: No response received from inverter.")
    
        command_client.loop_stop()
        command_client.disconnect()

    # Logic to read values using write addresses and map back to command names with 1 decimal precision
    raw_response = mqtt_storage.mqtt_storage_state['mqtt_response_data']
    response_data = {}
    
    for address, value in raw_response.items():
        try:
            # Convert value to float to handle potential decimal values
            float_val = float(value)
    
            # Round the value to 1 decimal place to match your json precision
            rounded_val = round(float_val, 1)
    
            # Handle swapped byte values for same read/write registers
            if address in same_read_write_regs:
                hex_val = f"{int(rounded_val):04X}"
                swapped = hex_val[2:] + hex_val[:2]
                transformed_value = int(swapped, 16)
                rounded_val = transformed_value
    
            response_data[address] = rounded_val  # default to rounded value
    
            # Map back to command name if possible
            matching_reg = next((reg for reg in registers if str(reg.get("read_address")) == address), None)
            if matching_reg and "commands" in matching_reg:
                # Reverse the command mapping: value → name (with rounded value)
                rev_command_map = {round(float(v), 1): k for k, v in matching_reg["commands"].items()}
                if rounded_val in rev_command_map:
                    response_data[address] = rev_command_map[rounded_val]  # use the name instead of raw value
    
        except Exception as e:
            response_data[address] = f"Error: {e}"

            
    if mqtt_storage.mqtt_storage_state["last_update_time"]:
        time_diff = datetime.now() - mqtt_storage.mqtt_storage_state["last_update_time"]
        seconds_ago = int(time_diff.total_seconds())
        st.info(f"📅 Last updated at: {mqtt_storage.mqtt_storage_state['last_update_time'].strftime('%Y-%m-%d %H:%M:%S')} ({seconds_ago} seconds ago)")
    else:
        st.warning("⚠️ No update has been received yet.")



    header_cols = st.columns([1, 1, 1, 1])
    with header_cols[0]: st.markdown("**Parameter**")
    with header_cols[1]: st.markdown("**Current Value**")
    with header_cols[2]: st.markdown("**New Value to be Set**")
    with header_cols[3]: st.markdown("**Allowable Range**")

    st.markdown("---")
    
    # Sort registers by 'Program No' if present and numeric
    try:
        registers.sort(key=lambda r: int(r.get("Program No", float('inf'))))
    except Exception as e:
        st.warning(f"⚠️ Could not sort by 'Program No': {e}")

    
    new_df, log_row = create_dataframe_from_mqtt(registers, response_data)
    df = new_df


    user_inputs = {}  # Collect user inputs for preset

    for idx, reg in enumerate(registers):
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 0.5, 1])

        with col1:
            is_preset = selected_preset != "None" and reg["name"] in presets_config.get(selected_preset, {})
            if is_preset:
                st.markdown(f"🔴 **{reg['name']}**")
            else:
                st.markdown(f"**{reg['name']}**")
            if is_preset:
                st.caption("From preset")
                
            # Special caption for parameters controlled by RMU
            if reg["name"] == "Low DC cut-off Voltage*":
                st.caption("*This parameter is controlled by RMU")

        with col2:
            current_row = df[df['Name'] == reg['name']]
            # print(df)
            st.code(str(current_row.iloc[0]["Value"]) if not current_row.empty else "N/A")

        selected_command = None
        write_val = None
        default_command = None
        
        if selected_preset != "None" and selected_preset in presets_config:
            default_command = presets_config[selected_preset].get(reg["name"])
        
        if "commands" in reg:
            with col3:
                command_keys = ["None"] + list(reg["commands"].keys())
                default_idx = command_keys.index(default_command) if default_command in command_keys else 0
                selected_command = st.selectbox(
                    " ",
                    command_keys,
                    index=default_idx,
                    key=f"cmd_{reg['name']}"
                )
                if selected_command != "None":
                    user_inputs[reg["name"]] = {
                        "type": "command",
                        "value": selected_command
                    }

        else:
            with col3:
                default_value = (
                    int(default_command) if default_command and str(default_command).isdigit()
                    else reg["range"][0] if "range" in reg else 0
                )
                write_val = st.number_input(
                    " ",
                    key=f"input_{idx}",
                    value=default_value,
                    min_value=reg["range"][0] if "range" in reg else None,
                    max_value=reg["range"][1] if "range" in reg else None,
                    format="%d"
                )
                if reg["name"] in presets_config.get(selected_preset, {}):
                    user_inputs[reg["name"]] = {
                        "type": "value",
                        "value": write_val
                    }

        with col4:
            try:
                if st.button("Set", key=f"set_{idx}"):
                    command_client = mqtt.Client()
                    ack_responses = []
        
                    def on_message(client, userdata, msg):
                        try:
                            payload = json.loads(msg.payload.decode())
                            if payload.get("rsp") in ["UP PROCESSING", "UP PROCESSED"]:
                                ack_responses.append(payload.get("rsp"))
                        except Exception as e:
                            st.error(f"⚠️ Failed to parse MQTT response: {e}")
        
                    command_client.on_message = on_message
                    command_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                    command_client.subscribe(f"/AC/1/{selected_topic}/Response")
        
                    # If a command is selected from the dropdown
                    if selected_command:
                        reg_addr = int(reg["write_address"])
                        value = int(reg["commands"][selected_command])
                        mqtt_message = f"UP#,{reg_addr:04}:{value:05}"
                        command_client.publish(MQTT_TOPIC, mqtt_message)
        
                    # If a value is typed manually
                    elif write_val is not None:
                        reg_addr = int(reg["write_address"])
                        value = int(write_val)
                        mqtt_message = f"UP#,{reg_addr:04}:{value:05}"
                        command_client.publish(MQTT_TOPIC, mqtt_message)
        
                    else:
                        st.warning("⚠️ No valid input to send.")
                        return
        
                    # Wait for acknowledgements (up to 5 seconds)
                    start_time = time.time()
                    while time.time() - start_time < 5:
                        command_client.loop(timeout=0.1)
                        if "UP PROCESSED" in ack_responses:
                            break
        
                    command_client.disconnect()
        
                    if "UP PROCESSED" in ack_responses:
                        st.success(f"✅ {reg['name']} parameter has been set successfully.")
                        mqtt_storage.mqtt_storage_state['mqtt_response_data'][reg["name"]] = (
                            selected_command if selected_command else write_val
                        )
                        df.loc[df["Name"] == reg["name"], "Value"] = (
                            selected_command if selected_command else write_val
                        )
                    else:
                        st.error(f"❌ Failed to confirm setting {reg['name']} parameter.")
        
            except Exception as e:
                st.error(f"⚠️ MQTT operation failed: {e}")

        with col5:
            if "description" in reg:
                st.caption(f"Options: {reg['description']}")
            elif "range" in reg:
                st.markdown(f"{reg['range'][0]} to {reg['range'][1]}")
            else:
                st.markdown(" ")

    # 🚀 Apply preset button at the end
    if selected_preset != "None" and user_inputs:
        if st.button("✅ Apply Preset"):
            command_client = mqtt.Client()
            command_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
            try:
                def on_publish(client, userdata, mid):
                    st.info(f"📤 Message published, MID: {mid}")
    
                command_client.on_publish = on_publish
    
                write_pairs = []
    
                for reg in registers:
                    if reg["name"] not in user_inputs:
                        continue
    
                    reg_address = reg.get("write_address")
                    entry = user_inputs[reg["name"]]
    
                    if entry["type"] == "command":
                        selected_command = entry["value"]
                        value = int(reg["commands"][selected_command])
                        write_pairs.append(f"{int(reg_address):04}:{value:05}")
    
                        mqtt_storage.mqtt_storage_state['mqtt_response_data'][reg["name"]] = selected_command
                        df.loc[df["Name"] == reg["name"], "Value"] = selected_command
    
                    elif entry["type"] == "value":
                        value = int(entry["value"])
                        write_pairs.append(f"{int(reg_address):04}:{value:05}")
    
                        mqtt_storage.mqtt_storage_state['mqtt_response_data'][reg["name"]] = value
                        df.loc[df["Name"] == reg["name"], "Value"] = value
    
                if write_pairs:
                    mqtt_message = f"UP#,{','.join(write_pairs)}"
                    command_client.publish(MQTT_TOPIC, mqtt_message)
                    st.success("✅ All preset values/commands published at once!")
    
                command_client.disconnect()
    
            except Exception as e:
                st.error(f"⚠️ MQTT operation failed: {e}")

