apt update
apt upgrade

apt install libportaudio2 libatlas-base-dev libespeak1 ffmpeg python3 python3-pip

git clone https://github.com/greerviau/VirtualAssistant.git
cd VirtualAssistant
pip3 install -r client_requirements.txt

git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard
./install.sh

mv va_client_service.service.sample /lib/systemd/system/va_client_service.service
systemctl enable va_client_service.service
systemctl start va_client_service.service