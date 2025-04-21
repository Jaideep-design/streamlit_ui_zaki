# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 11:55:41 2025

@author: Admin
"""

import serial
import time
import pandas as pd

# In[]

def write_to_serial(Serial_Details: dict, data_to_send: str):

    # Use the with statement for serial port
    with serial.Serial(
        port=Serial_Details['port'],
        baudrate=Serial_Details['baudrate'],
        parity=Serial_Details['parity'],
        stopbits=Serial_Details['stopbits'],
        bytesize=Serial_Details['bytesize'],
        timeout=Serial_Details['timeout']
    ) as ser:
        if ser.is_open:
            # print(f"Connected to {ser.port}")

        # Write data to the serial port
        # data_to_send = "Hello RS232!\r\n"
            ser.write(data_to_send)  # Encode string to bytes before sending
        # print(f"Sent: {data_to_send}")

        # Read data from the serial port
            time.sleep(1)  # Wait for a response
        if ser.in_waiting > 0:  # Check if there are bytes in the buffer
            received_data = ser.read(ser.in_waiting)  # Read and decode bytes
            # print(f"Received: {received_data}")
    return(received_data)



def create_remote_command_string(user_selection_dict: dict, debug: int = 0):
    RT_Dict_df = pd.read_excel("Remote_command_Dict.xlsx")

    df1 = pd.DataFrame()

    for byte_num in range(0,24):
        df1["Byte_"+str(byte_num)] = ["0x00"]

    for setting in user_selection_dict.keys():
        Name = "Byte_"+str(int(RT_Dict_df[RT_Dict_df["Byte type"]==setting]["Byte_number"].values[0]))
        if debug: print(setting)
        df1[Name] =  RT_Dict_df[(RT_Dict_df["Byte type"]==setting)&(RT_Dict_df["Action"]==user_selection_dict[setting])]["Set_HEX_value"].values

    df1["Byte_0"] = "0x24"
    df1["Byte_1"] = "0x16"
    df1["Byte_2"] = "0x03"
    df1["Byte_3"] = "0x01"
    df1["Byte_23"] = "0x23"
    df1["Byte_22"] = createChecksum(df1)

    msg_string = ""
    for byte_num in range(0,24):
        if debug: print ("Byte_",str(byte_num), " :",df1["Byte_"+str(byte_num)].values[0] )
        msg_string = msg_string + df1["Byte_"+str(byte_num)].values[0] + " "
        byte_list = [int(x, 16) for x in msg_string.split()]
        byte_array = bytes(byte_list)

    return(byte_array)


def createChecksum(df1):
    df_decimal = df1.applymap(lambda x: int(x, 16))
    sum_of_columns = df_decimal.iloc[:, 1:22].sum(axis=1).values[0]
    cs= hex(255 - sum_of_columns +1)
    return(cs)


def readACSettings(Serial_Details: dict):
    msg_string = "0x24 0x16 0x03 0x02 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0xE5 0x23"
    byte_list = [int(x, 16) for x in msg_string.split()]
    byte_array = bytes(byte_list)
    output = write_to_serial(Serial_Details=Serial_Details, data_to_send= byte_array)
    return(output)

# In[]
# user_selection_dict = {"Power": "On",
#                        "Mode" : "Cool mode",
#                        "Fan Level" : "High speed",
#                        "Set Temperature": "17°C",
#                        "Adjustable mode" : "L3" # "Adjustable mode": "Off", "L1","L2","L3","L4","L5"
# }

# Serial_Details = {"port":'COM9', # Replace with your RS232 port, e.g., 'COM1' (Windows) or '/dev/ttyS0' (Linux)
#                   "baudrate":9600, # Set the baud rate (match the device settings)
#                   "parity":serial.PARITY_NONE, # Parity settings: NONE, EVEN, ODD
#                   "stopbits":serial.STOPBITS_ONE, # Stop bits
#                   "bytesize": serial.EIGHTBITS, # Data bits
#                   "timeout": 1} # Read timeout in seconds


# command = create_remote_command_string(user_selection_dict)

# output = write_to_serial(Serial_Details = Serial_Details, data_to_send=command)


