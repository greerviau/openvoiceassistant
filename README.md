# Installing client on raspberry pi
Upgrade and install prerequisites
```
sudo apt update
sudo apt upgrade

sudo apt install libportaudio2
sudo apt install libatlas-base-dev
sudo apt install libespeak1
```
Clone the repository
```
git clone https://github.com/greerviau/VirtualAssistant.git
cd VirtualAssistant
```
Install packages
```
pip3 install -r client_requirements.txt
```
If using Adafruit I2S MEMS Microphone for input, follow wiring and installation instructions found [here](https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test)
