# Refactored version of data_reader.py
import json
import os
import time
import csv
import struct
import crcmod
import pandas as pd
from pymodbus.client import ModbusSerialClient

# -------------- Helper Functions -------------- #
def ConvertToSignedInt(unsigned_int):
    return unsigned_int - (1 << 16) if unsigned_int >= (1 << 15) else unsigned_int

def convert_to_little_Endian(val):
    return ((val & 0xFF) << 8) | ((val >> 8) & 0xFF)

# -------------- Modbus Client Setup -------------- #
simulate = True
client_sunnal = ModbusSerialClient(
    method="RTU",
    port='COM6',
    baudrate=2400,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=3,
    strict=False
)
client_sunnal.connect()

# -------------- Modbus Communication -------------- #
def build_modbus_write_command(slave_id, register_address, value):
    function_code = 0x06
    message = struct.pack('>B B H H', slave_id, function_code, register_address, value)
    crc16 = crcmod.predefined.mkCrcFun('modbus')
    crc = crc16(message)
    return message + struct.pack('<H', crc)

def read_from_modbus_slave(client, address, slave_address=5):
    try:
        return client.read_holding_registers(address, slave=slave_address)
    except Exception:
        return None

def write_to_modbus_slave(client, address, value, slave_address=5):
    try:
        return client.write_register(address, value, slave=slave_address)
    except Exception:
        return None

def read_register(address):
    if simulate:
        return 1234 + address
    result = read_from_modbus_slave(client_sunnal, address, slave_address=5)
    return result.registers[0] if result and not result.isError() else None

# -------------- Dataframe Builders -------------- #
def create_dataframe_from_registers(registers):
    table_data, log_row = [], {}
    bitflag_names = []

    for item in registers:
        reg_id = item["read_address"]
        raw_val = read_register(reg_id)
        value = convert_to_little_Endian(raw_val) if raw_val is not None else None

        if value is not None:
            if item.get("signed", False):
                value = ConvertToSignedInt(value)

            if item.get("type") == "bitflags":
                bits = format(value, '016b')[::-1]
                for idx, bit_val in enumerate(bits):
                    bit_name = item.get("bitflags", {}).get(str(idx))
                    if bit_name:
                        table_data.append({"Name": bit_name, "Value": int(bit_val), "Unit": item.get("unit", "")})
                        bitflag_names.append(bit_name)
            else:
                display_val = value * item.get("scale", 1)
                table_data.append({"Name": item["name"], "Value": display_val, "Unit": item.get("unit", "")})
                log_row[item["name"]] = display_val

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_row["Timestamp"] = timestamp
    table_data.append({"Name": "Timestamp", "Value": timestamp, "Unit": ""})

    return pd.DataFrame(table_data), bitflag_names, log_row

def create_dataframe_for_output_registers(registers, read_register):
    table_data, log_row = [], {}

    for item in registers:
        reg_id = item["read_address"]
        raw_val = read_register(reg_id)
        value = convert_to_little_Endian(raw_val) if raw_val is not None else None

        if value is not None:
            if item.get("signed", False):
                value = ConvertToSignedInt(value)
            value *= item.get("scale", 1)
            table_data.append({"Name": item["name"], "Value": value, "Unit": item.get("unit", "")})
            log_row[item["name"]] = value

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_row["Timestamp"] = timestamp
    table_data.append({"Name": "Timestamp", "Value": timestamp, "Unit": ""})

    return pd.DataFrame(table_data), log_row

def create_dataframe_from_mqtt(registers, latest_data):
    table_data, log_row = [], {}

    for item in registers:
        name = item["name"]
        value = latest_data.get(name)

        if value is not None:
            # Apply signed and scale if needed
            if item.get("signed", False):
                value = ConvertToSignedInt(value)
            value *= item.get("scale", 1)

            table_data.append({
                "Name": name,
                "Value": value,
                "Unit": item.get("unit", "")
            })
            log_row[name] = value
        else:
            table_data.append({
                "Name": name,
                "Value": "N/A",
                "Unit": item.get("unit", "")
            })

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    table_data.append({"Name": "Timestamp", "Value": timestamp, "Unit": ""})
    log_row["Timestamp"] = timestamp

    return pd.DataFrame(table_data), log_row

# -------------- Register Map & Logging -------------- #
def load_register_map(path='register_map.json'):
    try:
        with open(path, 'r') as f:
            return json.load(f).get("registers", [])
    except Exception:
        return []

def log_data(log_file, registers, log_row):
    file_exists = os.path.exists(log_file)
    fieldnames = ["Timestamp"] + [item["name"] for item in registers if item.get("type") != "bitflags"]
    with open(log_file, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_row)
