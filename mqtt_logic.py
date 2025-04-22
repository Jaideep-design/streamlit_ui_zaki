import time
import pandas as pd
from functools import partial
from Module1_mqtt_connection import connect_mqtt
from Module3_mqtt_handler import on_message, on_connect, parse_and_update
from shared_state import latest_data, latest_data_lock

def start_streaming(selected_topic):
    BROKER = "ecozen.ai"
    TOPIC = f"/AC/1/{selected_topic}/Datalog"
    CSV_PATH = "mqtt_logs_100.csv"
    dummydata_CSV_PATH = "mqtt_logs_11.csv"
    USE_DUMMY_DATA = False
    STREAM_INTERVAL = 1.0

    def dummy_stream(filepath):
        try:
            df = pd.read_csv(filepath)
            raw_messages = df['RawMessage'].dropna().tolist()
            for raw in raw_messages:
                parse_and_update(raw, latest_data, latest_data_lock, CSV_PATH)
                time.sleep(STREAM_INTERVAL)
        except Exception as e:
            print(f"❌ Error in dummy stream: {e}")

    if USE_DUMMY_DATA:
        print("🧪 Running in dummy CSV streaming mode...")

        # ui_thread = threading.Thread(target=launch_ui, args=(column_names, get_latest_data), daemon=True)
        # ui_thread.start()

        dummy_stream(dummydata_CSV_PATH)

    else:
        print("📡 Running in real MQTT mode...")

        # ui_thread = threading.Thread(target=launch_ui, args=(column_names, get_latest_data), daemon=True)
        # ui_thread.start()

        on_message_callback = partial(on_message, latest_data=latest_data, latest_data_lock=latest_data_lock)

        connect_mqtt(
            broker=BROKER,
            topic=TOPIC,
            on_message_callback=on_message_callback,
            on_connect_callback=on_connect,
            userdata={"topic": TOPIC, "csv_path": CSV_PATH}
        )
