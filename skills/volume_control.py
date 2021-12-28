def set_volume(volume):
    import alsaaudio
    m = alsaaudio.Mixer('Headphone')
    m.setvolume(volume)

def scale_volume(scale):
    import alsaaudio
    m = alsaaudio.Mixer('Headphone')
    volume = m.getvolume()
    volume = volume * scale
    m.setvolume(volume)