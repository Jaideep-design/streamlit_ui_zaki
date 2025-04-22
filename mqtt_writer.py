import paho.mqtt.client as mqtt
import streamlit as st
import time
import json
import pandas as pd
from shared_state import latest_data, latest_data_lock
from data_reader import create_dataframe_from_mqtt


def handle_parameter_write_mqtt(df, selected_topic):
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
        registers = []

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

    for idx, reg in enumerate(registers):
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 0.5, 1])

        with col1:
            st.markdown(f"**{reg['name']}**")

        with col2:
            current_row = df[df['Name'] == reg['name']]
            st.code(str(current_row.iloc[0]["Value"]) if not current_row.empty else "N/A")

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

        if set_btn:
            reg_address = reg.get("write_address")

            try:
                mqtt_client = mqtt.Client()

                def on_publish(client, userdata, mid):
                    st.info(f"📤 Message published successfully, MID: {mid}")

                mqtt_client.on_publish = on_publish
                mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

                if "commands" in reg:
                    hex_string = reg["commands"][selected_command]
                    hex_clean = hex_string.replace(" ", "")
                    register_hex = hex_clean[4:8]
                    value_hex = hex_clean[8:12]

                    reg_addr = int(register_hex, 16)
                    value = int(value_hex, 16)

                    mqtt_message = f"UP#,{reg_addr:04}:{value:05}"

                    st.info(f"🔧 Sending command `{selected_command}` for `{reg['name']}`")
                    st.code(mqtt_message, language="text")
                    mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                    time.sleep(2)
                    mqtt_client.disconnect()

                    with latest_data_lock:
                        latest_data[reg["name"]] = selected_command
                    df.loc[df["Name"] == reg["name"], "Value"] = selected_command

                    st.success(f"✅ `{reg['name']}` command `{selected_command}` sent via MQTT")

                else:
                    mqtt_message = f"UP#,{int(reg_address):04}:{int(write_val):05}"

                    st.info(f"🔧 Writing `{write_val}` to `{reg['name']}`")
                    st.code(mqtt_message, language="text")
                    mqtt_client.publish(MQTT_TOPIC, mqtt_message)
                    time.sleep(2)
                    mqtt_client.disconnect()

                    with latest_data_lock:
                        latest_data[reg["name"]] = write_val
                    df.loc[df["Name"] == reg["name"], "Value"] = write_val

                    st.success(f"✅ `{reg['name']}` written with value `{write_val}` via MQTT")

            except Exception as e:
                st.error(f"⚠️ MQTT operation failed: {e}")
