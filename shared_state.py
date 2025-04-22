# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 12:22:11 2025

@author: Admin
"""

# shared_state.py
import threading

latest_data_lock = threading.Lock()
latest_data = {"PV_V": 100, "PV_W": 100}

def get_latest_data():
    with latest_data_lock:
        return latest_data.copy()
