from setuptools import setup

setup(
    name='landsat_fetch',
    version='0.0.1',
    packages=['landsat_fetch'],
    python_requires='>=3.6,<4.0',
    install_requires=['pandas>=1.0,<2', 'gdal>=2.4,<3'],
    entry_points={
        'console_scripts': [
            'landsat_fetch=landsat_fetch.main:main',
        ],
    }
)