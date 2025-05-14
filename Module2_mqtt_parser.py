# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 16:12:01 2025

@author: Admin
"""

import MQTT_reference_mapping_v2 as mqtt_map
import pandas as pd

# df_dict = pd.read_excel(r"C:\Users\Admin\Desktop\Inverter_UI\Solar_AC_data_dictionary_version_3.xlsx", header=1)
# raw_hex = "01000300000000000000000116006400000000090001f4005c00070002000000dc1d56000000011068106800e6001200f000e601f4001200000000159f00010001000100020000001e00e6001e00e6010e011d011800dc0124003c0078001e000000230000000000050001000000000000000000000000190159010000000000000000000000000000000000000000000000000809042519293728000001600e10 IOT.COM0000102 AIRTELR02A07M08_OCP8991900992480943928F866082076503862020100020000000000000000"
raw_hex_deye = "0100021393ffedff6b0000ffffffed000c00000000000000000000000e004f0000004f000000000801000000000000000000000000008c00000000000008ad08aa08c901f101bb005a0426ffefffda0400040004e20abd006404000000000000000000fffdfff2138d138d000100100000010118015a01056700050000000000000000080705251314562300000bbe0ce4        IOT.COM0000204    AIRTELR02A07M08_OCP8991900992480943928F866082076503862020500020000000000000004"
url_2 = r"C:\Users\Admin\Desktop\Inverter_UI\Solar_AC_data_dictionary_version_1_deye_updated.xlsx"
url = "https://raw.githubusercontent.com/Jaideep-design/Streamlit_UI/main/Solar_AC_data_dictionary_version_3.xlsx"
df_dict = pd.read_excel(url, header=1)
df_dict_deye = pd.read_excel(url_2, header=1)

def parse_packet_deye(raw_hex_deye: str) -> dict:
    try:
        df_out = mqtt_map.process_all_registers(df_dict_deye, raw_hex_deye)
        return df_out
    except Exception as e:
        return {"Error": str(e)}
    
def parse_packet(raw_hex: str) -> dict:
    try:
        df_out = mqtt_map.process_all_registers(df_dict, raw_hex)
        return df_out
    except Exception as e:
        return {"Error": str(e)}

# def structure_for_ui(df: pd.DataFrame) -> dict:
#     """
#     Convert the processed DataFrame into a UI-friendly dict format.
#     """
#     if isinstance(df, dict):  # error case
#         return df
#     return df.to_dict(orient='records')[0]
# Mapping of raw df_input column keys to descriptive UI labels
# COLUMN_MAPPING = {
#     'W_STAT': 'Working State',
#     'AC_V': 'AC Input Voltage',
#     'AC_F': 'AC Input Frequency',
#     'PV_V': 'PV Input Voltage',
#     'PV_W': 'PV Input Power',
#     'BATT_V': 'Battery Voltage',
#     'BATT_CAP': 'Battery Capacity',
#     'BATT_CHG_I': 'Charging Current',
#     'BATT_DSCHG_I': 'Battery Discharge Current',
#     'OP_V': 'Output Voltage',
#     'OP_F': 'Output Frequency',
#     'OP_VA': 'Output Apparent Power',
#     'OP_W': 'Output Active Power',
#     'LOAD_PER': 'Load Percentage',
#     'DUAL_OP_SW_V': 'Dual Output Voltage Switch',
#     'DUAL_OP_SDN_V': 'Dual Output Shutdown Voltage',
#     'CPU_VER': 'Main CPU Version',
#     'CELL_BAL_SW': 'Cell Balancing Switch',
#     'BATT_PC': 'Battery Piece',
#     'NOM_OP_VA': 'Nominal Output Apparent Power',
#     'NOM_OP_W': 'Nominal Output Active Power',
#     'NOM_AC_V': 'Nominal AC Voltage',
#     'NOM_AC_I': 'Nominal AC Current',
#     'RATED_BATT_V': 'Rated Battery Voltage',
#     'NOM_OP_RATED_V': 'Nominal Output Voltage',
#     'NOM_OP_RATED_F': 'Nominal Output Frequency',
#     'NOM_OP_RATED_I': 'Nominal Output Current',
#     'Fan_Locked': 'Fan Locked',
#     'Over_Temperature': 'Over Temperature',
#     'Battery_Voltage_High': 'Battery Voltage High',
#     'Battery_Voltage_Low': 'Battery Voltage Low',
#     'Output_Shorted': 'Output Shorted',
#     'INV_Voltage_Over': 'INV Voltage Over',
#     'Over_Load': 'Over Load',
#     'Bus_Voltage_Over': 'Bus Voltage Over',
#     'Bus_Soft_Failed': 'Bus Soft Failed',
#     'Over_Current': 'Over Current',
#     'Bus_Voltage_Under': 'Bus Voltage Under',
#     'INV_Soft_Failed': 'INV Soft Failed',
#     'DC_Voltage_Over': 'DC Voltage Over',
#     'CT_Fault': 'CT Fault',
#     'INV_Voltage_Low': 'INV Voltage Low',
#     'PV_Voltage_High': 'PV Voltage High',
#     'Over_Temperature': 'Over Temperature',
#     'Battery_Voltage_Low': 'Battery Voltage Low',
#     'Over_Load': 'Over Load',
#     'Output_Power_Derating': 'Output Power Derating',
#     'PV_Energy_Weak': 'PV Energy Weak',
#     'AC_Voltage_High': 'AC Voltage High',
#     'Battery_Equalization': 'Battery Equalization',
#     'No Battery': 'No Battery',
#     'INT_TIME': 'Timestamp'
# }
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
    # 'DUAL_OP_SW_V': 'Dual Output Voltage Switch',
    # 'DUAL_OP_SDN_V': 'Dual Output Shutdown Voltage',
    # 'CPU_VER': 'Main CPU Version',
    # 'CELL_BAL_SW': 'Cell Balancing Switch',
    # 'BATT_PC': 'Battery Piece',
    # 'NOM_OP_VA': 'Nominal Output Apparent Power',
    # 'NOM_OP_W': 'Nominal Output Active Power',
    # 'NOM_GRID_V': 'Nominal AC Voltage',
    # 'NOM_GRID_I': 'Nominal AC Current',
    # 'RATED_BATT_V': 'Rated Battery Voltage',
    # 'NOM_OP_RATED_V': 'Nominal Output Voltage',
    # 'NOM_OP_RATED_F': 'Nominal Output Frequency',
    # 'NOM_OP_RATED_I': 'Nominal Output Current',
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
    # 'CHG_DSCHG_PRIO': 'Charger source priority',
    # 'OP_PRIO': 'Output Source priority',
    # 'MODE_SEL': 'AC input voltage range',
    # 'BATT_TYPE': 'Battery type',
    # 'OP_F_1': 'Output Frequency',
    # 'MAX_CHG_I': 'Max total charge current',
    # 'OP_V_1': 'Output voltage',
    # 'MAX_AC_CHG_I': 'Max utility charge current',
    # 'BCK_TO_UTIL': 'Comeback utility mode voltage (SBU)',
    # 'Bat_Volt_Back_To_Bat': 'Comeback battery mode voltage (SBU)',
    # 'BATT_CV_V': 'Bulk charging voltage',
    # 'BATT_FLOAT_V': 'Floating charging voltage',
    # 'BATT_V_SHUTOFF': 'Low Battery cut-off voltage',
    # 'EQ_V': 'Battery Equalization voltage',
    # 'EQ_TIME': 'Battery Equalized time',
    # 'EQ_TIMEOUT': 'Battery Equalized timeout',
    # 'EQ_INT': 'Battery Equalization interval',
    # 'GRID_OP': 'GRID-tie operation',
    # 'GRID_I': 'GRID-tie current',
    # 'LED_PATT_LIGHT': 'LED pattern light',
    # 'BUZZER_ALARM': 'Buzzer alarm (buzzer settings)',
    # 'LCD_BACKLIGHT': 'LCD backlight',
    # 'OL_AUTO_RST': 'Overload auto restart (overload restart setting)',
    # 'OT_AUTO_RST': 'Over temperature auto restart (over temperature restart setting)',
    # 'SRC_INTRPT_BEEP': 'Beeps while primary source interrupt (high priority source access, buzzer prompt)',
    # 'AUTO_RTN_LCD': 'Auto return to default display screen (return to LCD main page)',
    # 'BYPASS_TRANS_OL': 'Transfer to bypass @ overload',
    # 'EQ_ACT_IMM': 'Battery Equalization activated immediately',
    # 'RESTORE_DEFAULT': 'Restore Defaults (restore all settings in one click)'
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
