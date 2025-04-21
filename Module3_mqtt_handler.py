import os
import pandas as pd
from Module2_mqtt_parser import parse_packet, structure_for_ui

CSV_PATH = "mqtt_logs_100.csv"

def save_to_csv(row_df, csv_path):
    if not os.path.isfile(csv_path):
        row_df.to_csv(csv_path, index=False)
    else:
        row_df.to_csv(csv_path, mode='a', header=False, index=False)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to broker")
        # userdata = client._userdata  # 👈 pull it manually
        print(userdata) 
        client.subscribe(userdata["topic"])
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg, latest_data, latest_data_lock):
    print("📩 Message received")
    raw_hex = msg.payload.decode('utf-8')
    
    full_row = parse_packet(raw_hex)
    # Round numeric values
    if not isinstance(full_row, dict):
        full_row = round_values(full_row)
    full_row = full_row.copy()
    full_row.loc[:,"RawMessage"] = raw_hex
    full_row.loc[:,"updated_At"] = pd.Timestamp.now()
    structured_data = structure_for_ui(full_row)
    # structured_data = structure_for_ui(pd.read_csv(r"C:\Users\Admin\Downloads\df_input.csv"))

    print("🔧 Parsed & structured data ready for UI:", structured_data)

    # Save raw to CSV
    if not isinstance(full_row, dict):  # don't save error dicts
        save_to_csv(full_row, userdata["csv_path"])
    with latest_data_lock:
        print("M2 latest_data_lock: in")
        # global latest_data
        latest_data.clear()
        # latest_data.update(full_row.iloc[0].to_dict())
        latest_data.update(structured_data)

    # You can optionally forward structured_data to the UI (e.g., via a socket, shared memory, file, etc.)

def parse_and_update(raw_hex, latest_data, latest_data_lock, csv_path):
    """
    Parse raw hex message, save to CSV, and update shared latest_data dict.
    """
    try:
        full_row = parse_packet(raw_hex)
        # Round numeric values
        if not isinstance(full_row, dict):
           full_row = round_values(full_row)
        full_row['RawMessage'] = raw_hex
        full_row['updated_At'] = pd.Timestamp.now()
        # Save to CSV
        if not isinstance(full_row, dict):
            save_to_csv(full_row, csv_path)
        # Update shared state
        with latest_data_lock:
            latest_data.clear()
            latest_data.update(full_row.iloc[0].to_dict())
    except Exception as e:
        print(f"❌ Error parsing message: {e}")
        
def round_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Round numeric columns to one decimal place.
    """
    for col in df.select_dtypes(include=['float', 'int']).columns:
        try:
            df[col] = df[col].round(1)
        except Exception:
            pass
    return df