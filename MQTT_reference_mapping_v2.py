# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 14:29:46 2025

@author: Admin
"""

import pandas as pd
from datetime import datetime

def extract_bytes(hex_str, index, size):
    """Extract and convert the relevant slice from hex string to bytes."""
    return bytes.fromhex(hex_str[index: index + size]),hex_str[index: index + size]

def parse_value(hex_str, raw_bytes, dataformat, byteorder, signed, scaling_factor, size):
    """Parse raw bytes based on data format."""
    if dataformat == "DEC":
        value = int.from_bytes(raw_bytes, byteorder=byteorder, signed=signed)
        return value * scaling_factor
    elif dataformat == "BINARY":
        # value = int.from_bytes(raw_bytes, byteorder=byteorder, signed=signed)
        # return bin(value)[2:].zfill(size * 8)
        bin_str = ''.join(format(b, '08b') for b in raw_bytes)
        return bin_str
    elif dataformat == "ASCII":
        # return raw_bytes.decode('ascii', errors='ignore')
        return hex_str
    else:
        value = int.from_bytes(raw_bytes, byteorder=byteorder, signed=signed)
        return value * scaling_factor


def process_register_row(row, sample_packet, byteorder='big'):
    index = int(row['Index'])
    size = int(row['Size [byte]'])
    scaling_factor = float(row['Scaling factor']) if pd.notnull(row['Scaling factor']) else 1
    signed = str(row['Signed/Unsigned']).strip().lower() == 's'
    dataformat = str(row['Data format']).strip().upper()
    short_name = row['Short name']

    # Extract and parse
    raw_bytes, hex_str = extract_bytes(sample_packet, index, size)
    parsed_val = parse_value(hex_str, raw_bytes, dataformat, byteorder, signed, scaling_factor, size)
  
    # ✅ Apply custom logic (e.g., for RES2 or others)
    parsed_val = apply_custom_logic(short_name, parsed_val)
    return short_name, parsed_val

def apply_custom_logic(short_name, parsed_val):
    if short_name == "RES2":
        # dict_additional_flag_mapping = {
        #     0: "overcurrent",
        #     1: "batt_mode_high",
        #     2: "output_off_overcurrent"
        # }
        # parsed_val = dict_additional_flag_mapping.get(parsed_val, parsed_val)
        parsed_val = str(parsed_val[-3:])
    elif short_name == "W_STAT":
        dict_additional_flag_mapping =  {
        0: "Power On",
        1: "Test",
        2: "Stand By",
        3: "Battery Mode",
        4: "Line Mode",
        5: "Bypass",
        6: "Fault Mode",
        7: "ShutDown"
      }
        parsed_val = dict_additional_flag_mapping.get(parsed_val, parsed_val)
        
    elif short_name in ["INT TIME", "INT_TIME", ]:
      try:
          # Expected format: YYMMDDHHMMSS (e.g., 090425192937 = 2009-04-25 19:29:37)
          parsed_val = datetime.strptime(parsed_val, "%d%m%y%H%M%S")
      except Exception as e:
          parsed_val = f"Invalid timestamp: {parsed_val}"
    return parsed_val

def process_all_registers(df_dict, sample_packet):
    df_out = pd.DataFrame(index=[0])
    for _, row in df_dict.iterrows():
        try:
            name, val = process_register_row(row, sample_packet)
            df_out[name] = val
        except Exception as e:
            print(f"Error processing {row['Short name']}: {e}")
            df_out[row['Short name']] = None
    # df_out = process_res2_flags(df_out)
    df_out["BATT_W"] = df_out["BATT_V"] * df_out["BATT_I"]
    df_out = apply_bitfield_flags(df_out, "RES2", RES2_FLAGS, bit_width=3) 
    df_out = apply_bitfield_flags(df_out, "FLT", FLT_FLAGS)
    df_out = apply_bitfield_flags(df_out, "ALM", ALM_FLAGS)
    df_out = apply_bitfield_flags(df_out, "BIN_STAT", BIN_STAT_FLAGS)
    print("Decoded columns:", df_out.columns.tolist())
    print("Sample values:")
    print(df_out[["RES2", "FLT", "ALM", "BIN_STAT"]].head())
    return df_out

# def parse_res2_flags(res2_str: str) -> dict:
#     """
#     Takes a 3-bit binary string and returns a dict of individual RES2 flags.
#     Example: '010' → {'overcurrent': 0, 'batt_mode_high': 1, 'output_off_overcurrent': 0}
#     """
#     res2_str = res2_str[-3:].zfill(3)  # Ensure at least 3 bits
#     return {
#         "overcurrent": int(res2_str[2]),
#         "batt_mode_high": int(res2_str[1]),
#         "output_off_overcurrent": int(res2_str[0]),
#     }
# def process_res2_flags(df_out):
#     # Create a DataFrame of extracted flags from RES2
#     res2_flags_df = df_out["RES2"].fillna("000").astype(str).apply(parse_res2_flags).apply(pd.Series)
#     df_out["BATT_W"] = df_out["BATT_V"] * df_out["BATT_I"]
#     # Merge back with the original DataFrame
    
#     df_out = pd.concat([df_out, res2_flags_df], axis=1)
#     return df_out

RES2_FLAGS = {
    0: "overcurrent",
    1: "batt_mode_high",
    2: "output_off_overcurrent",
}

FLT_FLAGS = {
    0: "Fan_Locked",
    1: "Over_Temperature",
    2: "Battery_Voltage_High",
    3: "Battery_Voltage_Low",
    4: "Output_Shorted",
    5: "INV_Voltage_Over",
    6: "Over_Load",
    7: "Bus_Voltage_Over",
    8: "Bus_Soft_Failed",
    9: "Over_Current",
    10: "Bus_Voltage_Under",
    11: "INV_Soft_Failed",
    12: "DC_Voltage_Over",
    13: "CT_Fault",
    14: "INV_Voltage_Low",
    15: "PV_Voltage_High"
}

ALM_FLAGS ={
        0: "Fan Locked",
        1: "Over Temperature",
        2: "Battery Voltage Low",
        3: "Over Load",
        4: "Output Power Derating",
        5: "PV Energy Weak",
        6: "AC Voltage High",
        7: "Battery Equalization",
        8: "No Battery"
      }

BIN_STAT_FLAGS  = {
    0: "gps",
    1: "inverter comm fault",
    2: "Ac comm fault",
    3: "Sim detect",
    }

def parse_bitfield_flags(val: int or str, flag_map: dict, bit_width: int = 16) -> dict:
    """
    Converts an integer or binary string into a dictionary of flag names and their on/off states (0/1).
    Args:
        val: Integer or binary string.
        flag_map: A dict mapping bit positions (0 = LSB) to flag names.
        bit_width: Number of bits to pad binary representation to (default=16).
    Returns:
        Dict with flag names as keys and 0/1 as values.
    """
    try:
        if isinstance(val, str) and set(val) <= {'0', '1'}:
            bit_str = val.zfill(bit_width)
        else:
            bit_str = bin(int(val))[2:].zfill(bit_width)
        return {flag_map[i]: int(bit_str[-(i + 1)]) for i in range(bit_width) if i in flag_map}
    except Exception:
        return {flag_map[i]: None for i in range(bit_width) if i in flag_map}


def apply_bitfield_flags(df: pd.DataFrame, column_name: str, flag_map: dict, bit_width: int = 16) -> pd.DataFrame:
    """
    Applies flag parsing logic to a given bitfield column in a DataFrame.
    Args:
        df: DataFrame with raw data.
        column_name: The name of the column containing the bitfield value.
        flag_map: A dict mapping bit positions to flag names.
        bit_width: Total bits in the bitfield (default=16).
    Returns:
        Updated DataFrame with new columns for each flag.
    """
    flag_df = df[column_name].fillna(0).apply(lambda val: parse_bitfield_flags(val, flag_map, bit_width)).apply(pd.Series)
    return pd.concat([df, flag_df], axis=1)


# In[]
# df_dict=pd.read_excel(r"C:\Users\Admin\OneDrive\Documents\UI\Solar_AC_data_dictionary_version_1.xlsx", header=1)
# sample_packet = '01000408db01f400000000011800640000000008db01f406e806f9002a000000dc1d56000000011068106800e6001200f000e601f4001200000000159f00010001000100020000001e00e6001e00e6010e011d011800dc0124003c0078001e00000026000000000005000100000000000000000000010118015e010569000500000000000000000000000000000000000000000810042516112827000002230ed8        IOT.COM0000102    AIRTELR02A07M08_OCP8991900992480943928F866082076503862020500020000000000000000'
# # Assume sample_packet is a hex string with no spaces (e.g., from earlier: "01010001000a00...")
# df_out = process_all_registers(df_dict, sample_packet)
# print(df_out.T)
