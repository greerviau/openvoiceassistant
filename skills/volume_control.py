def set_volume(volume):
    import alsaaudio
    m = alsaaudio.Mixer()
    m.setvolume(volume)

def scale_volume(scale):
    import alsaaudio
    m = alsaaudio.Mixer()
    volume = m.getvolume()
    volume = volume * scale
    m.setvolume(volume)