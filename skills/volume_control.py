from subprocess import call

def set_volume(volume, device):
    '''
    scale = 200 + int(55.0 * (volume/100.0))
    if volume == 0:
        scale = 0
    '''
    call(['sudo', 'amixer', 'cset', 'numid=1', f'{volume}%'])
