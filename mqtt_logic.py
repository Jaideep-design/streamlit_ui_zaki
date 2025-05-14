import time
import pandas as pd
from functools import partial
from Module1_mqtt_connection import connect_mqtt
from Module3_mqtt_handler import on_message_stream, on_connect, parse_and_update
from shared_state import latest_data, latest_data_lock

# Global clients
streaming_client = None
current_topic = None

def start_streaming(selected_topic):
    global streaming_client  # No need for current_topic now

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
        dummy_stream(dummydata_CSV_PATH)

    else:
        print("📡 Running in real MQTT mode...")

        if streaming_client is not None:
            # Get old topic from existing client's userdata (if available)
            old_userdata = streaming_client._userdata
            old_topic = old_userdata.get("current_topic") if old_userdata else None

            if old_topic:
                print(f"🛑 Disconnecting from old topic: {old_topic}")
                streaming_client.unsubscribe(old_topic)

            streaming_client.loop_stop()
            streaming_client.disconnect()

        # Setup updated userdata with new topic and tracking key
        userdata = {
            "topic": TOPIC,
            "csv_path": CSV_PATH,
            "current_topic": None  # Will be updated in on_connect
        }

        on_message_callback = partial(on_message_stream, latest_data=latest_data, latest_data_lock=latest_data_lock)

        streaming_client = connect_mqtt(
            broker=BROKER,
            topic=TOPIC,
            on_message_callback=on_message_callback,
            on_connect_callback=on_connect,
            userdata=userdata
        )

