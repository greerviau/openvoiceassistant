from subprocess import call

def set_volume(volume, device):
    scale = 200 + int(55.0 * (volume/100.0))
    if volume == 0:
        scale = 0
    call(["amixer", '-D', f'hw:{device}', 'sset', 'Playback', f'{scale}'])
