import time
import paho.mqtt.client as mqtt

MQTT_TCAS_HOST = "localhost"
MQTT_TCAS_CHANNEL = "cedricpump.de/thluebeck/tcas"

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("cedricpump.de/thluebeck/tcas")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_TCAS_HOST, 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.

while True:
    time.sleep(0.5)
    string = '{"mode": "BROADCAST", "address": "ef542760-4715-40b1-abc4-349b881ef7c2", "type": "SHORT_SQUITTER", "data": {"alt": 5400.0, "lat": 53.805747173744344, "long": 10.714933253660258, "vs": 0.0, "gs": 140.0}}'
    client.publish("cedricpump.de/thluebeck/tcas", payload=string, qos=0, retain=False)
