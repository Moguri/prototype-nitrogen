from setuptools import setup
from game.blenderpanda import pman


pman.build()


setup(
    name='nitrogen',
    options={
        'build_apps': {
            'copy_paths': [
                ('game', '.'),
                '.pman',
            ],
            'gui_apps': {
                'nitrogen-game': 'game/main.py',
            },
            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],
            'deploy_platforms': [
                'manylinux1_x86_64',
            ],
            'include_modules': {
                'nitrogen-game': [
                    'bamboo.rendermanager'
                ],
            },
            'exclude_modules': {
                '*': ['game'],
            },
        }
    }
)
