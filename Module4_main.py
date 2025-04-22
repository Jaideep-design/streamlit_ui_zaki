import threading
from functools import partial
from Module1_mqtt_connection import connect_mqtt
from Module3_mqtt_handler import on_message, on_connect, parse_packet, save_to_csv, parse_and_update
from Module5_ui_display import launch_ui
import pandas as pd
import time

# Shared state
latest_data_lock = threading.Lock()
latest_data = {"PV_V": 100,
               "PV_W": 100}
current_data = {}

def get_latest_data():
    with latest_data_lock:
        return latest_data.copy()

# Constants
BROKER = "ecozen.ai"
TOPIC = "/AC/1/EZMCISAC00001/Datalog"
CSV_PATH = "mqtt_logs_100.csv"
dummydata_CSV_PATH = "mqtt_logs_11.csv"
USE_DUMMY_DATA = False  # Set to True for dummy data

STREAM_INTERVAL = 1.0  # seconds between dummy messages

# Dummy stream: parse and update latest_data

def dummy_stream(filepath):
    df = pd.read_csv(filepath)
    raw_messages = df['RawMessage'].dropna().tolist()
    for raw in raw_messages:
        parse_and_update(raw, latest_data, latest_data_lock, CSV_PATH)
        time.sleep(STREAM_INTERVAL)
        
# Dummy MQTT message
DUMMY_MESSAGE = (
    "01000300000000090907ba0115006400110000090701f304df04d8001e000000dc1d56000000011068106800e6001200f000e601f4001200000000159f00010001000100020000001400e6001e00e6010e011d011800dc0124003c0078001e000c002e0000000000050001000000000000ffffffef00000000000000000000000000000000000000000000000000000000000000000000000000000c150425111802220000005b0dac        IOT.COM0000203    AIRTELR02A07M08_OCP8991900992480943928F866082076503862020100020000000000000007"
)

# ✅ Real-time getter
def get_latest_data():
    with latest_data_lock:
        return latest_data.copy()

# ✅ Main logic
def mqtt_message_logic(TOPIC=TOPIC):
    userdata = {"topic": TOPIC, "csv_path": CSV_PATH}

    column_names = ['PV_V', 'PV_W', 'BATT_V', 'BATT_CAP', 'BATT_CHG_I']

    if USE_DUMMY_DATA:
        print("🧪 Running in dummy CSV streaming mode...")

        # Start UI thread with getter
        # ui_thread = threading.Thread(
        #     target=launch_ui, args=(column_names, get_latest_data), daemon=True
        # )
        # ui_thread.start()

        # Simulate real-time updates to latest_data from dummy stream
        dummy_stream_thread = threading.Thread(
            target=run_dummy_streaming_logic, args=(dummydata_CSV_PATH,), daemon=True
        )
        dummy_stream_thread.start()

    else:
        print("📡 Running in real MQTT mode...")

        # Optionally start a UI thread (if needed)
        # ui_thread = threading.Thread(target=launch_ui, args=(column_names, get_latest_data), daemon=True)
        # ui_thread.start()

        # Set up MQTT with shared state
        on_message_callback = partial(
            on_message, latest_data=latest_data, latest_data_lock=latest_data_lock
        )

        connect_mqtt(
            broker=BROKER,
            topic=TOPIC,
            on_message_callback=on_message_callback,
            on_connect_callback=on_connect,
            userdata=userdata
        )

# ✅ Dummy streaming logic updates latest_data like MQTT would
def run_dummy_streaming_logic(csv_path):
    import pandas as pd
    import time

    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        with latest_data_lock:
            latest_data.update(row.to_dict())
        time.sleep(1)  # simulate real-time stream

# In[]
# # BROKER = "ecozen.ai"
# # TOPIC = "/AC/1/EZMCISAC00001/Datalog"
# # CSV_PATH = "mqtt_logs_100.csv"

# # if __name__ == "__main__":
# #     userdata = {"topic": TOPIC, "csv_path": CSV_PATH}
# #     connect_mqtt(broker = BROKER, topic = TOPIC, on_message_callback=on_message, on_connect_callback=on_connect,userdata =userdata )

# from Module1_mqtt_connection import connect_mqtt
# from Module3_mqtt_handler import on_message, on_connect, parse_packet, save_to_csv
# from Module5_ui_display import launch_ui
# import pandas as pd

# import threading
# from functools import partial



# latest_data_lock = threading.Lock()
# latest_data = {}

# def get_latest_data():
#     with latest_data_lock:
#         return latest_data.copy()


# # Constants
# BROKER = "ecozen.ai"
# TOPIC = "/AC/1/EZMCISAC00001/Datalog"
# CSV_PATH = "mqtt_logs_100.csv"
# USE_DUMMY_DATA = False  # 🔁 Switch this to False for real MQTT

# # Dummy MQTT message (as string)
# DUMMY_MESSAGE = (
#     "01000300000000090907ba0115006400110000090701f304df04d8001e000000dc1d56000000011068106800e6001200f000e601f4001200000000159f00010001000100020000001400e6001e00e6010e011d011800dc0124003c0078001e000c002e0000000000050001000000000000ffffffef00000000000000000000000000000000000000000000000000000000000000000000000000000c150425111802220000005b0dac        IOT.COM0000203    AIRTELR02A07M08_OCP8991900992480943928F866082076503862020100020000000000000007"
# )

# if __name__ == "__main__":
#     userdata = {"topic": TOPIC, "csv_path": CSV_PATH}

#     if USE_DUMMY_DATA:
#         print("🧪 Running in dummy test mode...")
#         df = parse_packet(DUMMY_MESSAGE)
#         print(df.head())
#         save_to_csv(df, CSV_PATH)
#         print(f"✅ Dummy data saved to {CSV_PATH}")
        
#         # 🚀 Launch UI with structured data
#         structured_data_dict = df.iloc[0].to_dict()
#         launch_ui(structured_data_dict)
#     else:
#         print("📡 Running in real MQTT mode...")
#         column_names = ['PV_V', 'PV_W', 'BATT_V', 'BATT_CAP', 'BATT_CHG_I']  # Adjust as needed
#         # Start the UI in a separate thread
#         ui_thread = threading.Thread(target=launch_ui, args=(column_names, get_latest_data))
#         ui_thread.start()
#         # Create a partial function with additional arguments
#         on_message_callback = partial(on_message, latest_data=latest_data, latest_data_lock=latest_data_lock)

#         connect_mqtt(broker=BROKER, topic=TOPIC, on_message_callback=on_message_callback, on_connect_callback=on_connect, userdata=userdata)
