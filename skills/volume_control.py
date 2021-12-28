from subprocess import call

def set_volume(volume, device):
    import alsaaudio
    call(["amixer", '-D', f'hw:{device}', 'sset', 'Speaker', f'{volume}%'])

def scale_volume(scale):
    import alsaaudio
    m = alsaaudio.Mixer('Headphone')
    volume = m.getvolume()
    volume = volume * scale
    m.setvolume(volume)