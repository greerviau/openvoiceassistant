# Open Voice Assistant
Open Voice Assistant is a fully offline, locally hosted and completely customizable Voice Assistant. Designed to be an opensource alternative to voice assistants like Alexa and Google home.

# Deployment
OVA functions as a HUB + Node (satelite) network. 

## [HUB](https://github.com/greerviau/openvoiceassistant-hub/tree/develop)
The HUB handles all the processing for the core components including Audio Transcription, Natural Language Understanding and Text to Speech Synthesis. It also handles all of the skills and integrations, which can be configured along with all the other settings for the HUB as well as all the settings for Nodes connected to the HUB.

## [Node](https://github.com/greerviau/openvoiceassistant-node/tree/develop)
The Nodes act as ears and a mouth for the HUB. They are designed to be lightweight in order to be deployed on small embeded devices such as Raspberry Pi's. (Hopefully support will be added in the future for cheaper and more power efficienct WIFI enabled microcontroller devices such as esp32's).

Please check out the respective repos for more information on installation and usage.

# [Release Notes](RELEASES.md)