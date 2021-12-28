def set_volume(volume):
    import alsaaudio
    m = alsaaudio.Mixer('PCM')
    m.setvolume(volume)

def scale_volume(scale):
    import alsaaudio
    m = alsaaudio.Mixer('PCM')
    volume = m.getvolume()
    volume = volume * scale
    m.setvolume(volume)