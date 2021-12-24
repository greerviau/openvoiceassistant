import alsaaudio

def set_volume(volume):
    m = alsaaudio.Mixer()
    m.setvolume(volume)

def scale_volume(scale):
    m = alsaaudio.Mixer()
    volume = m.getvolume()
    volume = volume * scale
    m.setvolume(volume)