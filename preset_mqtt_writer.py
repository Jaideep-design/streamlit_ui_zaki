import paho.mqtt.client as mqtt
import streamlit as st
import time
import json
import pandas as pd
from shared_state import latest_data, latest_data_lock
from data_reader import create_dataframe_from_mqtt
from presets_config import presets_config

def handle_parameter_write_mqtt(df, selected_topic, selected_preset=None):
    st.subheader("✍️ Write Parameters to Inverter (MQTT)")

    MQTT_BROKER = "ecozen.ai"
    MQTT_PORT = 1883
    MQTT_TOPIC = f"/AC/1/{selected_topic}/Command"

    try:
        with open('output.json', 'r') as f:
            register_data = json.load(f)
            registers = register_data.get("registers", [])
    except Exception as e:
        st.error(f"Failed to load parameter config: {e}")
        return

    if not registers:
        st.info("No write parameters defined in output.json")
        return

    st.header("⚙️ Inverter Write Parameters")
    header_cols = st.columns([1, 1, 1, 1])
    with header_cols[0]: st.markdown("**Parameter**")
    with header_cols[1]: st.markdown("**Current Value**")
    with header_cols[2]: st.markdown("**New Value to be Set**")
    with header_cols[3]: st.markdown("**Allowable Range**")

    st.markdown("---")

    new_df, log_row = create_dataframe_from_mqtt(registers, latest_data)

    if df is not None and not df.empty:
        df = pd.concat([df, new_df], ignore_index=True)
    else:
        df = new_df

    user_inputs = {}  # Collect user inputs for preset

    for idx, reg in enumerate(registers):
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 0.5, 1])

        with col1:
            st.markdown(f"**{reg['name']}**")

        with col2:
            current_row = df[df['Name'] == reg['name']]
            st.code(str(current_row.iloc[0]["Value"]) if not current_row.empty else "N/A")

        selected_command = None
        write_val = None
        default_command = None

        if selected_preset != "None" and selected_preset in presets_config:
            default_command = presets_config[selected_preset].get(reg["name"])

        if "commands" in reg:
            with col3:
                command_keys = list(reg["commands"].keys())
                default_idx = command_keys.index(default_command) if default_command in command_keys else 0
                selected_command = st.selectbox(
                    " ",
                    command_keys,
                    index=default_idx,
                    key=f"cmd_{reg['name']}"
                )
                if reg["name"] in presets_config.get(selected_preset, {}):
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
            if selected_preset == "None":
                if st.button("Set", key=f"set_{idx}"):
                    # Logic to send MQTT message for this individual parameter
                    if selected_command:
                        hex_string = reg["commands"][selected_command]
                        hex_clean = hex_string.replace(" ", "")
                        register_hex = hex_clean[4:8]
                        value_hex = hex_clean[8:12]
                        reg_addr = int(register_hex, 16)
                        value = int(value_hex, 16)
                        mqtt_message = f"UP#,{reg_addr:04}:{value:05}"
                        mqtt_client = mqtt.Client()
                        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                        mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                        st.success(f"✅ {reg['name']} command {selected_command} sent")
                    elif write_val is not None:
                        mqtt_message = f"UP#,{int(reg['write_address']):04}:{int(write_val):05}"
                        mqtt_client = mqtt.Client()
                        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                        mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                        st.success(f"✅ {reg['name']} value {write_val} written")


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
            mqtt_client = mqtt.Client()
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

            try:
                def on_publish(client, userdata, mid):
                    st.info(f"📤 Message published, MID: {mid}")

                mqtt_client.on_publish = on_publish

                for reg in registers:
                    if reg["name"] not in user_inputs:
                        continue

                    reg_address = reg.get("write_address")
                    entry = user_inputs[reg["name"]]

                    if entry["type"] == "command":
                        selected_command = entry["value"]
                        hex_string = reg["commands"][selected_command]
                        hex_clean = hex_string.replace(" ", "")
                        register_hex = hex_clean[4:8]
                        value_hex = hex_clean[8:12]

                        reg_addr = int(register_hex, 16)
                        value = int(value_hex, 16)

                        mqtt_message = f"UP#,{reg_addr:04}:{value:05}"
                        mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                        st.success(f"✅ {reg['name']} command {selected_command} sent")

                        with latest_data_lock:
                            latest_data[reg["name"]] = selected_command
                        df.loc[df["Name"] == reg["name"], "Value"] = selected_command

                    elif entry["type"] == "value":
                        value = entry["value"]
                        mqtt_message = f"UP#,{int(reg_address):04}:{int(value):05}"
                        mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                        st.success(f"✅ {reg['name']} value {value} written")

                        with latest_data_lock:
                            latest_data[reg["name"]] = value
                        df.loc[df["Name"] == reg["name"], "Value"] = value

                    time.sleep(1.5)

                mqtt_client.disconnect()

            except Exception as e:
                st.error(f"⚠️ MQTT operation failed: {e}")