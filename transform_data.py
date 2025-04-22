# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 14:32:06 2025

@author: Admin
"""

import streamlit as st
import json
import pandas as pd
from data_reader import create_dataframe_for_output_registers

def handle_parameter_write(df, client_sunnal, read_register, write_to_modbus_slave, build_modbus_write_command,create_dataframe_from_registers, simulate):
    try:
        with open('output.json', 'r') as f:
            register_data = json.load(f)
            registers = register_data.get("registers", [])
    except Exception as e:
        st.error(f"Failed to load parameter config: {e}")
        registers = []

    if not registers:
        st.info("No write parameters defined in output.json")
        return

    st.header("⚙️ Inverter Write Parameters")
    header_cols = st.columns([1, 1, 1, 1])
    with header_cols[0]: st.markdown("**Parameter**")
    with header_cols[1]: st.markdown("**Current Value**")
    with header_cols[2]: st.markdown("**New Value to be Set**")
    with header_cols[3]: st.markdown("**Allowable Range (Simulated)**")

    st.markdown("---")
    
    new_df, log_row = create_dataframe_for_output_registers(registers, read_register)

    # Append the new dataframe to the existing one
    if df is not None and not df.empty:
        df = pd.concat([df, new_df], ignore_index=True)
    else:
        df = new_df
 
    
    for idx, reg in enumerate(registers):
        # Define single-line compact layout
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 0.5, 1])  # Name, Current, Input, Set, Range

        with col1:
            st.markdown(f"**{reg['name']}**")

        with col2:
            current_row = df[df['Name'] == reg['name']]
            if not current_row.empty:
                val = current_row.iloc[0]["Value"]
                st.code(str(val))
            else:
                st.code("N/A")
        
        # Initialize button state and value holder
        set_btn = False
        selected_command = None
        write_val = None

        if "commands" in reg:
            with col3:
                selected_command = st.selectbox(
                    " ", list(reg["commands"].keys()), key=f"cmd_{reg['name']}"
                )
            with col4:
                st.write("")
                set_btn = st.button("Set", key=f"set_{idx}")
        else:
            with col3:
                write_val = st.number_input(
                    " ",
                    key=f"input_{idx}",
                    value=reg["range"][0] if "range" in reg else 0,
                    min_value=reg["range"][0] if "range" in reg else None,
                    max_value=reg["range"][1] if "range" in reg else None,
                    format="%d"
                )
            with col4:
                st.write("")
                set_btn = st.button("Set", key=f"set_{idx}")

        with col5:
            if "description" in reg:
                st.caption(f"Options: {reg['description']}")
            elif "range" in reg:
                st.markdown(f"{reg['range'][0]} to {reg['range'][1]}")
            else:
                st.markdown(" ")

        # Execute Set button
        if set_btn:
            reg_address = reg["write_address"]
        
            if "commands" in reg:
                hex_string = reg["commands"][selected_command]
                hex_bytes = bytes.fromhex(hex_string.replace(" ", ""))
        
                if simulate:
                    st.success(f"✅ (Simulated) `{reg['name']}` command `{selected_command}` selected")
                    st.code(hex_string, language="text")
        
                    # Optional: simulate update
                    df.loc[df["Name"] == reg["name"], "Value"] = selected_command
                else:
                    try:
                        # Extract register address and value from hex string
                        # Example hex: 05 06 13 99 00 02 DD 24
                        # Index 2-3: register address (13 99 = 5017), Index 4-5: value (00 02 = 2)
        
                        register_hex = hex_string.replace(" ", "")[4:8]
                        value_hex = hex_string.replace(" ", "")[8:12]
        
                        reg_addr = int(register_hex, 16)
                        value = int(value_hex, 16)
        
                        response = client_sunnal.write_register(reg_addr, value, slave=5)
        
                        if response.isError():
                            st.error(f"❌ Failed to send `{reg['name']}` command `{selected_command}`")
                        else:
                            st.success(f"✅ `{reg['name']}` command `{selected_command}` sent")
                            st.code(hex_string, language="text")
                            df.loc[df["Name"] == reg["name"], "Value"] = selected_command
                    except Exception as e:
                        st.error(f"⚠️ Error sending command: {e}")
            else:
                try:
                    if simulate:
                        cmd = build_modbus_write_command(1, reg_address, int(write_val))
                        st.success(f"✅ (Simulated) `{reg['name']}` written with value `{write_val}`")
                        st.code(" ".join(f"{byte:02X}" for byte in cmd), language="text")
        
                        # Update the df with the new value
                        df.loc[df["Address"] == reg_address, "Value"] = write_val
                    else:
                        response = write_to_modbus_slave(client_sunnal, reg_address, int(write_val), slave_address=5)
        
                        if response.isError():
                            st.error(f"❌ Failed to write `{reg['name']}`")
                        else:
                            cmd = build_modbus_write_command(1, reg_address, int(write_val))
                            st.success(f"✅ `{reg['name']}` written with value `{write_val}`")
                            st.code(" ".join(f"{byte:02X}" for byte in cmd), language="text")
        
                            # Update the df with the new value
                            df.loc[df["Address"] == reg_address, "Value"] = write_val
                except Exception as e:
                    st.error(f"⚠️ Error writing to register: {e}")


