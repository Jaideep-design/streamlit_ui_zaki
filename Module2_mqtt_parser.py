# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 16:12:01 2025

@author: Admin
"""

import MQTT_reference_mapping_v2 as mqtt_map
import pandas as pd

# df_dict = pd.read_excel(r"C:\Users\Admin\Desktop\Inverter_UI\Solar_AC_data_dictionary_version_3.xlsx", header=1)
# raw_hex = "01000300000000093403c3010a00410007000008fa01f402df02bf0012000000dc3bc4000000011068106800e6001200f000e601f4001200000000159f00010001000000020000003200e6003200e6010e0120011400ee0124003c0078001e000c00300000000000050001000000000000fffffff9010111015e01056900010000000000000000000000000000000000000000000000000000000008260525151446180000137a1004        IOT.COM0000205    AIRTELR02A07M08_OCP8991900992665204740F860738070206747020100020000000000000001"
# raw_hex_deye = "0100021393ffedff6b0000ffffffed000c00000000000000000000000e004f0000004f000000000801000000000000000000000000008c00000000000008ad08aa08c901f101bb005a0426ffefffda0400040004e20abd006404000000000000000000fffdfff2138d138d000100100000010118015a01056700050000000000000000080705251314562300000bbe0ce4        IOT.COM0000204    AIRTELR02A07M08_OCP8991900992480943928F866082076503862020500020000000000000004"
# url_2 = r"C:\Users\Admin\Desktop\Inverter_UI\Solar_AC_data_dictionary_version_1_deye_updated.xlsx"
url = "https://raw.githubusercontent.com/Jaideep-design/Streamlit_UI/main/Solar_AC_data_dictionary_version_3.xlsx"
df_dict = pd.read_excel(url, header=1)
# df_dict_deye = pd.read_excel(url_2, header=1)

# def parse_packet_deye(raw_hex_deye: str) -> dict:
#     try:
#         df_out = mqtt_map.process_all_registers(df_dict_deye, raw_hex_deye)
#         return df_out
#     except Exception as e:
#         return {"Error": str(e)}
    
def parse_packet(raw_hex: str) -> dict:
    try:
        df_out = mqtt_map.process_all_registers(df_dict, raw_hex)
        return df_out
    except Exception as e:
        return {"Error": str(e)}

COLUMN_MAPPING = {
    'W_STAT': 'Working State',
    'GRID_V': 'Grid Input Voltage',
    'GRID_F': 'Grid Input Frequency',
    'PV_V': 'PV Input Voltage',
    'PV_W': 'PV Input Power',
    'BATT_V': 'Battery Voltage',
    'BATT_CAP': 'Battery Capacity',
    'BATT_CHG_I': 'Charging Current',
    'BATT_DSCHG_I': 'Battery Discharge Current',
    'OP_V': 'Output Voltage',
    'OP_F': 'Output Frequency',
    'OP_VA': 'Output Apparent Power',
    'OP_W': 'Output Active Power',
    'LOAD_PER': 'Load Percentage',
    'Fan Locked': 'Fan Locked',
    'Over Temperature': 'Over Temperature',
    'Battery_Voltage_High': 'Battery Voltage High',
    'Battery_Voltage_Low': 'Battery Voltage Low',
    'Output_Shorted': 'Output Shorted',
    'INV_Voltage_Over': 'INV Voltage Over',
    'Over_Load': 'Over Load',
    'Bus_Voltage_Over': 'Bus Voltage Over',
    'Bus_Soft_Failed': 'Bus Soft Failed',
    'Over_Current': 'Over Current',
    'Bus_Voltage_Under': 'Bus Voltage Under',
    'INV_Soft_Failed': 'INV Soft Failed',
    'DC_Voltage_Over': 'DC Voltage Over',
    'CT_Fault': 'CT Fault',
    'INV_Voltage_Low': 'INV Voltage Low',
    'PV_Voltage_High': 'PV Voltage High',
    'Battery Voltage Low': 'Battery Voltage Low',
    'Output Power Derating': 'Output Power Derating',
    'PV Energy Weak': 'PV Energy Weak',
    'AC Voltage High': 'AC Voltage High',
    'Battery Equalization': 'Battery Equalization',
    'No Battery': 'No Battery',
    'INT TIME': 'Timestamp',
    'AC_PWR_STAT': 'AC Power_Status',
    'AC_SET_TEMP': 'AC Set_temperature',
    'Ac comm fault': 'AC Comm Fault',
    'inverter comm fault': 'Inverter Comm Fault'
}

def structure_for_ui(df: pd.DataFrame) -> dict:
    """
    Convert the processed DataFrame into a UI-friendly dict format using COLUMN_MAPPING.
    """
    if isinstance(df, dict):  # error case
        return df
    # Rename columns according to mapping
    df_renamed = df.rename(columns=COLUMN_MAPPING)
    # Keep only the mapped descriptive columns
    mapped_cols = [COLUMN_MAPPING[key] for key in COLUMN_MAPPING if key in df.columns]
    # Extract first row as dict
    record = df_renamed[mapped_cols].iloc[0].to_dict()
    return record
