# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 14:58:54 2025

@author: Admin
"""


import serial_communication as SC
import ModbusMaster as MM
import pandas as pd
import numpy as np
from pymodbus.client import ModbusSerialClient
import serial
import time
import os
from datetime import datetime
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian



def ConvertToSignedInt(unsigned_int):
    signed_int = unsigned_int - (1 << 16) if unsigned_int >= (1 << 15) else unsigned_int
    return(signed_int)

def FindCapLevel(current_level: str , Cap_Power_Map:  pd.DataFrame, deficit: int ):
    currentPower = Cap_Power_Map[Cap_Power_Map["Cap_level"]==current_level]["Power"].values[0]
    Cap_Power_Map["diff"] = Cap_Power_Map["Power"] - currentPower + deficit
    if Cap_Power_Map[Cap_Power_Map["diff"]<0].empty:
        target_level = 1
    else:
        target_diff = Cap_Power_Map[Cap_Power_Map["diff"]<0]["diff"].max()
        target_level = Cap_Power_Map[Cap_Power_Map["diff"] == target_diff].Cap_level.values[0]
    return(target_level)

def convert_to_little_Endian(Big_Endian_value):
    return ((Big_Endian_value & 0xFF) << 8) | ((Big_Endian_value >> 8) & 0xFF)

def calc_SOC_CC(SOC_last,Batt_C,Batt_V,step_time,V_max = 28.8):
    if Batt_C > 0:
        if Batt_V > V_max:
            SOC = 1
    else:
        SOC = max(0,SOC_last - Batt_C*step_time/(30*3600))
        SOC = min (100, SOC)
    return SOC

# In[]

# Create a ModbusSerialClient instance
client_sunnal = ModbusSerialClient(
    method="RTU",        # RTU transmission mode
    port='COM6',         # Replace with the actual port (e.g., 'COM4' or '/dev/ttyUSB0')
    baudrate=2400,       # Match the slave configuration
    parity='N',          # No parity
    stopbits=1,          # One stop bit
    bytesize=8,          # 8 data bits
    timeout=3,            # Timeout for communication
    strict=False        # Allow some timing variations
)

Sunnal_address = 4501
Sunnal_slave = 5

# LOG_FILE  = "Test1"
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# %%
step_time = 0.5
LOG_FILE = "inverter_register_log.csv"  # CSV file for logging

# Mapping of register addresses to column names
register_mapping = {
    4501: "Working State",
    4502: "AC input voltage",
    4503: "AC input frequency",
    4504: "PV input voltage",
    4505: "PV input power",
    4506: "Battery voltage",
    4507: "Battery capacity %",
    4508: "Charging current",
    4509: "Battery discharge current",
    4510: "Output voltage",
    4511: "Output frequency",
    4512: "Output apparent power",
    4513: "Output active power",
    4514: "AC output Load %",
    4516: "Dual Output Voltage Switch",
    4517: "Dual Output Shutdown Voltage",
    4518: "Main CPU version",
    4519: "Cell balancing switch",
    4520: "Battery Piece",
    4521: "Nominal output apparent power",
    4522: "Nominal output active power",
    4523: "Nominal AC voltage",
    4524: "Nominal AC current",
    4525: "Rated battery voltage",
    4526: "Nominal output voltage",
    4527: "Nominal output frequency",
    4528: "Nominal output current",
    4529: "Fault Code",       # Register index 28
    4530: "Alarm Code",       # Register index 29
    4536: "Charger Priority",
    4537: "Output Priority",
    4538: "Mode Select",
    4539: "BatteryType",
    4540: "Output Freq",
    4541: "Max Chg Cur",
    4542: "Output Volt",
    4543: "Max AC Chg Cur",
    4544: "Back To Utility",
    4545: "Bat Volt Back To Bat",
    4546: "Bat CV Volt",
    4547: "Bat Float Volt",
    4548: "Battery Volt Under",
    4549: "Equalization voltage",
    4550: "Equalization time",
    4551: "Equalization timeout",
    4552: "Equalization interval",
    4556: "PV charge status",
    4557: "NTC MAX Temperature",
    4558: "PV Grid On Power",
    4559: "GRID-tie operation",
    4560: "GRID-tie current",
    4561: "Led pattern light",
    4562: "Equalization activated",
    4563: "PV2 input voltage",
    4564: "PV2 input power"
}

while True:
    time.sleep(step_time)
    try:
        inveter_data_read = MM.read_from_modbus_slave(client_sunnal, address=4501, count=64, slave_address=5)

        data = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        for i, raw_value in enumerate(inveter_data_read.registers):
            reg_address = 4501 + i

            # Special handling for registers 28 and 29
            if i == 28:  # Fault Code
                fault_code_bin = format(raw_value, '016b')[::-1]
                print(f"Fault Code (bin): {fault_code_bin}")
                data["Fault Code (bin)"] = fault_code_bin
                continue
            elif i == 29:  # Alarm Code
                alarm_code_bin = format(raw_value, '016b')[::-1]
                print(f"Alarm Code (bin): {alarm_code_bin}")
                data["Alarm Code (bin)"] = alarm_code_bin
                continue

            col_name = register_mapping.get(reg_address, f"Register_{reg_address}")
            data[col_name] = convert_to_little_Endian(raw_value)

        df = pd.DataFrame([data])
        print(df)

        file_exists = os.path.isfile(LOG_FILE)
        df.to_csv(LOG_FILE, mode='a', header=not file_exists, index=False)

    except Exception as err:
        print(f"Error: {err}")
        pass




# # In[]
# step_time = 0.5

# while True:
#     time.sleep(step_time)
#     try:
#         inveter_data_read = MM.read_from_modbus_slave(client_sunnal, address = 4501, count = 45,slave_address = 5 )

#         load_W = convert_to_little_Endian(inveter_data_read.registers[12])
#         Battery_current_chg = convert_to_little_Endian(inveter_data_read.registers[7])
#         Battery_current_dch = convert_to_little_Endian(inveter_data_read.registers[8])
#         Battery_current_Net = Battery_current_dch - Battery_current_chg
#         Battery_voltage = convert_to_little_Endian(inveter_data_read.registers[5])*0.1
#         Grid_voltage = convert_to_little_Endian(inveter_data_read.registers[9])*0.1
#         PV_W = convert_to_little_Endian(inveter_data_read.registers[4])*0.1
#         fault_code = format(inveter_data_read.registers[28], '016b')[::-1]
#         alarm_code = format(inveter_data_read.registers[29], '016b')[::-1]

#         df = pd.DataFrame({
#             'Timestamp': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
#             'Batt_V': [Battery_voltage],
#             'Batt_I': [Battery_current_Net],
#             'load_W' : [load_W],
#             'Solar_W': [PV_W ],
#             'Grid_V' : [Grid_voltage],
#             'Fault_code' : [fault_code],
#             'Alarm_code' : [alarm_code]
#         })

#         print(df)

#         file_exists = os.path.isfile(LOG_FILE)
#         df.to_csv(LOG_FILE, mode='a', header=not file_exists, index=False)
#         print(f"Logged {COUNT} registers to {LOG_FILE}")
#     except Exception as err:
#         print(f'Error:{err}')
#         pass

# In[]