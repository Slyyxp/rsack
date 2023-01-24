from setuptools import setup, find_packages
from rsack.version import __version__

setup(
    name="rsack",
    description="A Multi-purpose downloader.",
    long_description="Read more at https://github.com/Slyyxp/rsack",
    url="https://github.com/Slyyxp/rsack",
    author="Slyyxp",
    author_email="slyyxp@protonmail.com",
    version=__version__,
    packages=find_packages(),
    install_requires=["requests==2.25.1", "mutagen==1.45.1", "loguru==0.5.3", "pycryptodome==3.15.0"],
    entry_points={
                'console_scripts': [
                    'rsack = rsack.main:main'
                ]
    })
