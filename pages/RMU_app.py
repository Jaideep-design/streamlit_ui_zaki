import streamlit as st
st.set_page_config(layout="wide")
import paho.mqtt.client as mqtt
from zoneinfo import ZoneInfo
from datetime import datetime
import threading
import ast
import json
import time
import pandas as pd
import warnings
import sys
import os
import re

warnings.filterwarnings('ignore')
try:
    current_dir = os.path.dirname(__file__)
except NameError:
    # Fallback if __file__ is not defined (e.g. interactive session)
    current_dir = os.getcwd()

# Add parent directory (Inverter_UI) to sys.path
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import shared_state
@st.cache_data
def load_mqtt_topics():
    return [f"EZMCISAC{str(i).zfill(5)}" for i in range(1, 301)]

# === MQTT Configuration
BROKER = "ecozen.ai"
PORT = 1883
DEVICE_MESSAGE = "#PARGET&"

# === Shared flags
client_connected = threading.Event()
response_received = threading.Event()
mqtt_ready = threading.Event()

# === MQTT Client
client = mqtt.Client()

# === MQTT Callbacks ===
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully")
        client.subscribe(userdata['subscribe_topic'])
        mqtt_ready.set()           # Allows main thread to proceed
        client_connected.set()     # Allows publisher thread to proceed
    else:
        print(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8').strip().replace("'", '"')
        print("\nRaw payload:", payload)
        data = ast.literal_eval(payload.replace('"', "'"))
        parsed_data = dict(item.split(":") for item in data["rsp"].split(",") if item)
        shared_state.shared_response["data"] = parsed_data
        print(f"Latest Response Updated: {shared_state.shared_response}")
        response_received.set()
    except Exception as e:
        print(f"Error parsing message: {e}")
        
def render_compact_table_with_buttons(df, key_prefix="btn"):
    for index, row in df.iterrows():
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(f"<div style='font-size:15px;padding:2px 6px'>{row['Parameter']}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='font-size:15px;padding:2px 6px'>{row['Value']}</div>", unsafe_allow_html=True)
        with col3:
            if st.button("Set", key=f"{key_prefix}_{index}"):
                st.success(f"Set action triggered for **{row['Parameter']}**")

# === Streamlit UI ===
st.title("MQTT Device Monitor")

devices = load_mqtt_topics()

# Track device selection across reruns
if "previous_device" not in st.session_state:
    st.session_state.previous_device = None

device = st.selectbox("Select Device", devices)

if device:
    # Check if the device selection has changed
    if st.session_state.previous_device != device:
        shared_state.shared_response.clear()  # Clear cached response when device changes
        st.session_state.previous_device = device  # Update stored device

    subscribe_topic = f"/AC/1/{device}/Response"
    publish_topic = f"/AC/1/{device}/Command"
    st.write(f"Subscribe Topic: `{subscribe_topic}`")
    st.write(f"Publish Topic: `{publish_topic}`")

# MQTT Thread Starters
def start_mqtt(userdata):
    client.on_connect = on_connect
    client.on_message = on_message
    client.user_data_set(userdata)
    client.connect(BROKER, PORT, 60)
    client.loop_start()

def publisher_loop(userdata):
    if client_connected.wait(timeout=10):  
        time.sleep(1)  
        print("\nSending request...")
        client.publish(userdata['publish_topic'], DEVICE_MESSAGE)
    else:
        print("MQTT client not connected in time.")

############################################################################################
with st.expander("Change Device Log Frequency"):
    st.markdown("### Set New Log Frequency (in seconds)")

    # Frequency range for validation
    min_freq = 1
    max_freq = 120

    new_freq_input = st.text_input("Enter frequency (1 to 120 seconds)", key="log_freq_input")

    if st.button("Set Log Frequency", key="set_frequency"):
        try:
            if not new_freq_input:
                st.warning("⚠️ Please enter a frequency value.")
            else:
                try:
                    new_freq = int(new_freq_input)
                except ValueError:
                    st.error("❌ Enter a valid integer.")
                    raise st.stop()

                if not (min_freq <= new_freq <= max_freq):
                    st.warning(f"⚠️ Frequency must be between {min_freq} and {max_freq} seconds.")
                    raise st.stop()

                # Prepare MQTT client and listen for acknowledgment
                ack_responses = []
                command_client = mqtt.Client()

                def on_message_ack(client, userdata, msg):
                    try:
                        payload = msg.payload.decode()
                        if "Updated" in payload or "OK" in payload:
                            ack_responses.append("Updated")
                    except Exception as e:
                        st.error(f"⚠️ Failed to parse response: {e}")

                command_client.on_message = on_message_ack
                command_client.connect(BROKER, PORT, 60)
                command_client.subscribe(subscribe_topic)

                # Prepare frequency change command
                mqtt_command = f"#DLI{new_freq}&"
                command_client.publish(publish_topic, mqtt_command)

                # Wait for acknowledgment
                start_time = time.time()
                while time.time() - start_time < 5:
                    command_client.loop(timeout=0.1)
                    if "Updated" in ack_responses:
                        break

                command_client.disconnect()

                if "Updated" in ack_responses:
                    st.success(f"✅ Frequency changed to {new_freq} seconds successfully.")
                else:
                    st.error("❌ No acknowledgment received for frequency change.")

        except Exception as e:
            st.error(f"⚠️ MQTT operation failed: {e}")

#############################################################################################                

if st.button("Read Parameters"):
    with st.spinner("Initializing device..."):
        shared_state.shared_response.clear()  # Clear again to be extra safe
        userdata = {
            'device': device,
            'subscribe_topic': subscribe_topic,
            'publish_topic': publish_topic
        }

        mqtt_ready.clear()
        response_received.clear()
        client_connected.clear()

        # Start MQTT client thread
        threading.Thread(target=start_mqtt, args=(userdata,), daemon=True).start()

        # Wait for MQTT to connect & subscribe
        if mqtt_ready.wait(timeout=5):
            publisher_thread = threading.Thread(target=publisher_loop, args=(userdata,), daemon=True)
            publisher_thread.start()
            publisher_thread.join()

            # Wait for response
            if response_received.wait(timeout=15):
                st.success("Parameters received successfully.")
            else:
                st.error("Device is offline or not responding.")
        else:
            st.error("MQTT client failed to connect to broker.")

# === Display shared response
resp = shared_state.shared_response
# Display updated response
if resp.get("data"):
    # Mapping for readable labels
    param_mapping = {
        "P1": "Set Loop_Time",
        "P2": "Set Step_Time",
        "P3": "Set Wait_time",
        "P4": "Set Batt_dch_th_high",
        "P5": "Set Batt_chg_th_high",
        "P6": "Set Batt_dch_th_low",
        "P7": "Set Batt_chg_th_low",
        "P8": "Set SOC_th_low",
        "P9": "Set SOC_th_high",
        "P10": "Set SOC_th_chg",
        "P11": "Set SOC_Vmax",
        "P12": "Set Batt_Capacity",
        "P13": "Set Batt_dch_Max",
        "P14": "Set Batt_low_cut_off_high",
        "P15": "Set Batt_low_cut_off_Normal",
        "P16": "Set Max_stop_time",
        "P17": "Set Min_PV_volt",
        "P18": "Set Min_grid_Voltage",
        "P19": "Set min_start_time",
        "P20": "Set Batt_present_threshold",
        "P21": "Set BATTV_th_low",
        "P22": "Set BATTV_th_high",
        "P23": "Data log frequency"
    }

    # Apply mapping
    mapped_data = {param_mapping.get(k, k): v for k, v in resp["data"].items()}
    df = pd.DataFrame(mapped_data.items(), columns=["Parameter", "Value"])

    # Chunking and layout
    chunk_size = 11
    table_chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

    ist_time = datetime.now(ZoneInfo("Asia/Kolkata"))
    st.write(f"Last Updated: {ist_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    col1, col2 = st.columns(2)

    with open("RMU_parameters.json", "r") as f:
        parameter_config = json.load(f)  # Not json.loads
    
    parameter_lookup = {entry["PARAMETER NAME"]: entry for entry in parameter_config["registers"]}
    
    with col1:
        st.subheader("RMU Parameters - 1")
    
        if len(table_chunks) > 0:
            for index, row in table_chunks[0].iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
                param = row["Parameter"]
                c1.markdown(f"<div style='font-size:15px;padding:2px 6px'>{param}</div>", unsafe_allow_html=True)
                c2.markdown(f"<div style='font-size:15px;padding:2px 6px'>{row['Value']}</div>", unsafe_allow_html=True)
    
                # Validate parameter presence in JSON
                if param not in parameter_lookup:
                    c3.warning("Not in config")
                    continue
    
                reg = parameter_lookup[param]
                identifier = reg["IDENTIFIER"]
                limits_str = reg.get("DATA(Limits)", "0-65535")  # fallback to wide range if not specified
    
                # Use dropdown if DROPDOWN key exists
                if "DROPDOWN" in reg and isinstance(reg["DROPDOWN"], list):
                    new_value = c3.selectbox(f"New value for {param}", reg["DROPDOWN"], key=f"dropdown_{index}")
                else:
                    new_value = c3.text_input(f"New value for {param}", key=f"input_{index}")
    
                if c4.button("Set", key=f"set_{index}"):
                    try:
                        if not new_value:
                            st.warning("⚠️ Please enter or select a value.")
                            continue
    
                        # Try to convert to int
                        try:
                            value = int(new_value)
                        except ValueError:
                            st.error("❌ Enter a valid integer.")
                            continue
    

                        # Extract two integers (positive or negative) using regex
                        limits = re.findall(r'-?\d+', limits_str)
                        if len(limits) != 2:
                            st.error(f"⚠️ Could not parse limits for '{param}': '{limits_str}'")
                            continue
                        
                        lower, upper = int(limits[0]), int(limits[1])
    
                        if not (lower <= value <= upper):
                            st.warning(f"⚠️ Value for '{param}' must be between {lower} and {upper}.")
                            continue
    
                        # Setup MQTT
                        ack_responses = []
                        command_client = mqtt.Client()
    
                        def on_message_write(client, userdata, msg):
                            try:
                                payload = json.loads(msg.payload.decode())
                                if payload.get("rsp") == "Updated":
                                    ack_responses.append("Updated")
                            except Exception as e:
                                st.error(f"⚠️ Failed to parse response: {e}")
    
                        command_client.on_message = on_message_write
                        command_client.connect(BROKER, PORT, 60)
                        command_client.subscribe(subscribe_topic)
    
                        mqtt_message = f"{identifier},{value}&"
                        command_client.publish(publish_topic, mqtt_message)
    
                        # Wait for ack
                        start_time = time.time()
                        while time.time() - start_time < 5:
                            command_client.loop(timeout=0.1)
                            if "Updated" in ack_responses:
                                break
    
                        command_client.disconnect()
    
                        if "Updated" in ack_responses:
                            st.success(f"✅ '{param}' set to {value} successfully.")
                            df.loc[df["Parameter"] == param, "Value"] = value
                        else:
                            st.error(f"❌ No confirmation received for '{param}'.")
    
                    except Exception as e:
                        st.error(f"⚠️ MQTT operation failed: {e}")

    
    with col2:
        st.subheader("RMU Parameters - 2")
        if len(table_chunks) > 0:
            for index, row in table_chunks[1].iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
                param = row["Parameter"]
                c1.markdown(f"<div style='font-size:15px;padding:2px 6px'>{param}</div>", unsafe_allow_html=True)
                c2.markdown(f"<div style='font-size:15px;padding:2px 6px'>{row['Value']}</div>", unsafe_allow_html=True)
    
                # Validate parameter presence in JSON
                if param not in parameter_lookup:
                    c3.warning("Not in config")
                    continue
    
                reg = parameter_lookup[param]
                identifier = reg["IDENTIFIER"]
                limits_str = reg.get("DATA(Limits)", "0-65535")  # fallback to wide range if not specified
    
                # Use dropdown if DROPDOWN key exists
                if "DROPDOWN" in reg and isinstance(reg["DROPDOWN"], list):
                    new_value = c3.selectbox(f"New value for {param}", reg["DROPDOWN"], key=f"dropdown_{index}")
                else:
                    new_value = c3.text_input(f"New value for {param}", key=f"input_{index}")
    
                if c4.button("Set", key=f"set_{index}"):
                    try:
                        if not new_value:
                            st.warning("⚠️ Please enter or select a value.")
                            continue
    
                        # Try to convert to int
                        try:
                            value = int(new_value)
                        except ValueError:
                            st.error("❌ Enter a valid integer.")
                            continue
    
                        # Parse limits
                        limits = limits_str.replace("to", "-").replace(" ", "").split("-")
                        lower, upper = int(limits[0]), int(limits[1])
    
                        if not (lower <= value <= upper):
                            st.warning(f"⚠️ Value for '{param}' must be between {lower} and {upper}.")
                            continue
    
                        # Setup MQTT
                        ack_responses = []
                        command_client = mqtt.Client()
    
                        def on_message_write(client, userdata, msg):
                            try:
                                payload = json.loads(msg.payload.decode())
                                if payload.get("rsp") == "Updated":
                                    ack_responses.append("Updated")
                            except Exception as e:
                                st.error(f"⚠️ Failed to parse response: {e}")
    
                        command_client.on_message = on_message_write
                        command_client.connect(BROKER, PORT, 60)
                        command_client.subscribe(subscribe_topic)
    
                        mqtt_message = f"{identifier},{value}&"
                        command_client.publish(publish_topic, mqtt_message)
    
                        # Wait for ack
                        start_time = time.time()
                        while time.time() - start_time < 5:
                            command_client.loop(timeout=0.1)
                            if "Updated" in ack_responses:
                                break
    
                        command_client.disconnect()
    
                        if "Updated" in ack_responses:
                            st.success(f"✅ '{param}' set to {value} successfully.")
                            df.loc[df["Parameter"] == param, "Value"] = value
                        else:
                            st.error(f"❌ No confirmation received for '{param}'.")
    
                    except Exception as e:
                        st.error(f"⚠️ MQTT operation failed: {e}")
else:
    st.warning("No data received yet.")
