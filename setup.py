from setuptools import setup

setup(
    name='landsat_fetch',
    version='0.0.1',
    packages=['landsat_fetch', 'landsat_fetch.operations', 'landsat_fetch.workflows'],
    python_requires='>=3.6,<4.0',
    install_requires=['pandas>=0.25,<1', 'numpy>=1.17,<2', 'ffmpeg-python>=0.2,<0.3', 'gdal>=3.0,<4'],
    entry_points={
        'console_scripts': [
            'landsat_fetch=landsat_fetch.main:main',
        ],
    }
)