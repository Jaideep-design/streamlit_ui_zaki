# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 16:10:46 2025

@author: Admin
"""

import paho.mqtt.client as mqtt

def connect_mqtt(broker, topic, on_message_callback, on_connect_callback=None,userdata=None):
    client = mqtt.Client()
    client.user_data_set(userdata) 
    # client._userdata = userdata  # 👈 force-set it here
    client.on_connect = on_connect_callback
    client.on_message = on_message_callback
    print("🚀 Connecting to broker...")
    client.connect(broker, 1883, 60)
    client.loop_start()  # 🔄 Non-blocking!
    return client  # return the client so you can later disconnect it if needed
