import streamlit as st
st.set_page_config(layout="wide")
import paho.mqtt.client as mqtt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import threading
import ast
import json
import time
import pandas as pd
import warnings
import sys
import os
import uuid

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
def load_mqtt_topics():
    return [f"EZMCISAC{str(i).zfill(5)}" for i in range(1, 61)]
    
# Manual refresh button
if st.button("REFRESH"):
    unique_key = str(uuid.uuid4())  # generate a new key every time
    st_autorefresh(interval=1000, limit=1, key=unique_key)  # 1 second interval, reruns only once

st.write("Last updated at:", time.strftime("%Y-%m-%d %H:%M:%S"))

# # === Global store for background thread
# shared_response = {"data": {}, "timestamp": None}

# === MQTT Configuration
BROKER = "ecozen.ai"
PORT = 1883
DEVICE_MESSAGE = "#PARGET&"

# === Shared flags
client_connected = threading.Event()
response_received = threading.Event()

# === MQTT Client
client = mqtt.Client()

# === MQTT Callbacks ===
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker for {userdata['device']}")
        client_connected.set()
        result, _ = client.subscribe(userdata['subscribe_topic'])
        if result != mqtt.MQTT_ERR_SUCCESS:
            print(f"Subscription failed: {mqtt.error_string(result)}")
        else:
            print(f"Subscribed to {userdata['subscribe_topic']}")
    else:
        print(f"Failed to connect. Code: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8').strip().replace("'", '"')
        print("\nRaw payload:", payload)
        data = ast.literal_eval(payload.replace('"', "'"))
        parsed_data = dict(item.split(":") for item in data["rsp"].split(",") if item)
        shared_state.shared_response["data"] = parsed_data
        shared_state.shared_response["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

device = st.selectbox("Select Device", devices)

if device:
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
        if not response_received.wait(timeout=15):
            print("No response within timeout.")
        else:
            print("Response received successfully.")
        response_received.clear()
    else:
        print("MQTT client not connected in time.")
            

if st.button("Read Parameters"):
    with st.spinner("Initializing device..."):
        userdata = {
            'device': device,
            'subscribe_topic': subscribe_topic,
            'publish_topic': publish_topic
        }

        threading.Thread(target=start_mqtt, args=(userdata,), daemon=True).start()
        threading.Thread(target=publisher_loop, args=(userdata,), daemon=True).start()
        st.success(f"Device {device} connected and click REFRESH button to display!")


# === Display shared response
resp = shared_state.shared_response
# Display updated response
if resp["data"]:
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

    st.write(f"Last Updated: {resp['timestamp']}")
    
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
