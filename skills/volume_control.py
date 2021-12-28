from subprocess import call

def set_volume(volume, device):
    scale = int(255.0 * (volume/100.0))
    print(scale)
    call(["amixer", '-D', f'hw:{device}', 'sset', 'Playback', f'{scale}%'])

def scale_volume(scale):
    m = alsaaudio.Mixer('Headphone')
    volume = m.getvolume()
    volume = volume * scale
    m.setvolume(volume)