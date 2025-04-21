# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 13:30:22 2025

@author: Admin
"""

# from pymodbus.client import ModbusSerialClient
from pymodbus.client import ModbusSerialClient

# import logging
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
# import struct


# # Configure logging
# logging.basicConfig()
# log = logging.getLogger()
# log.setLevel(logging.DEBUG)

# Create a ModbusSerialClient instance
client = ModbusSerialClient(
    method='rtu',        # RTU transmission mode
    port='COM3',         # Replace with the actual port (e.g., 'COM4' or '/dev/ttyUSB0')
    baudrate=9600,       # Match the slave configuration
    parity='N',          # No parity
    stopbits=1,          # One stop bit
    bytesize=8,          # 8 data bits
    timeout=1            # Timeout for communication
)


# # Connect to the slave
# if client.connect():
#     print("Connected to Modbus slave.")

#     try:
#         # Example 1: Read holding registers (function code 0x03)
#         address = 190  # Start address
#         count = 8    # Number of registers to read
#         response = client.read_holding_registers(address, count, unit=1)  # `unit` is the slave ID

#         if response.isError():
#             print(f"Error reading holding registers: {response}")
#         else:
#             print(f"Holding registers from {address} to {address + count - 1}: {response.registers}")

#         # Example 2: Write a single holding register (function code 0x06)
#         register_address = 3
#         value_to_write = 123
#         write_response = client.write_register(register_address, value_to_write, unit=1)

#         if write_response.isError():
#             print(f"Error writing to register {register_address}: {write_response}")
#         else:
#             print(f"Successfully wrote value {value_to_write} to register {register_address}.")

#         # Example 3: Write multiple holding registers (function code 0x10)
#         start_address = 4
#         values_to_write = [100, 200, 300]
#         multiple_write_response = client.write_registers(start_address, values_to_write, unit=1)

#         if multiple_write_response.isError():
#             print(f"Error writing multiple registers: {multiple_write_response}")
#         else:
#             print(f"Successfully wrote values {values_to_write} starting at register {start_address}.")

#     except Exception as e:
#         print(f"An exception occurred: {e}")

#     # Close the connection
#     client.close()
#     print("Connection closed.")
# else:
#     print("Unable to connect to Modbus slave.")

# def modbus_crc16(data: bytes) -> bytes:
#     crc = 0xFFFF  # Initial value
#     for byte in data:
#         crc ^= byte  # XOR with the byte
#         for _ in range(8):  # Process 8 bits
#             if crc & 0x0001:  # Check if the lowest bit is 1
#                 crc = (crc >> 1) ^ 0xA001  # Shift right and apply polynomial
#             else:
#                 crc >>= 1  # Just shift right
#     return bytes([crc & 0xFF, (crc >> 8) & 0xFF])  # Return CRC in little-endian order


# def create_frame(Starting_address: int = 0x1195,Number_of_registers: int = 0x000E):
#     address = 0x01
#     Function = 0x03
#     # Starting_address = 0x1195
#     start_address_bytes = struct.pack('>H', Starting_address)
#     # Number_of_registers = 0x000E
#     num_registers_bytes = struct.pack('>H', Number_of_registers)

#     frame = bytearray([address, Function])  # Modbus request frame
#     frame.extend(start_address_bytes)  # Add starting address
#     frame.extend(num_registers_bytes)  # Add number of registers
#     crc = modbus_crc16(frame)
#     frame.extend(crc)
#     print(f"Modbus RTU Frame: {' '.join(f'{byte:02X}' for byte in frame)}")
#     return frame

# def read_from_modbus_slave(client):
#     frame_out = create_frame()
#     if client.connect():
#         print("Connected to Modbus slave.")

#         try:
#             # Example 1: Read holding registers (function code 0x03)
#             response = client._serial.execute(frame_out)
#             print(f"Response: {' '.join(f'{byte:02X}' for byte in response)}")
#         except Exception as e:
#             print(f"An exception occurred: {e}")

#         # Close the client connection
#         client.close()
#     return response

def read_from_modbus_slave(client, address, count, slave_address=1):
    if client.connect():
        # print("Connected to Deye over Modbus.")
        try:
            # Example 1: Read holding registers (function code 0x03)
            response = client.read_holding_registers(address, count, slave=slave_address)
            # if response.isError():
                # print(f"Error reading holding registers: {response}")
            # else:
                # print(f"Holding registers from {address} to {address + count - 1}: {response.registers}")
        except Exception as e:
                # print(f"An exception occurred: {e}")
                pass
        # Close the client connection
        client.close()
    return response

# read_from_modbus_slave(client, address = 190, count = 8)

def write_to_modbus_slave(client, address, value, slave_address=1):
    """
    Writes a value to a Modbus register at the given address.
    """
    if client.connect():
        try:
            response = client.write_register(address, value, slave=slave_address)
            # Optionally check response:
            # if response.isError():
            #     print(f"Error writing to register {address}: {response}")
        except Exception as e:
            print(f"Exception while writing to register {address}: {e}")
        finally:
            client.close()
        return response
