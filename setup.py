from setuptools import setup, find_packages

setup(
    name="rsack",
    description="A Multi-purpose downloader.",
    long_description="Read more at https://github.com/Slyyxp/rsack",
    url="https://github.com/Slyyxp/rsack",
    author="Slyyxp",
    author_email="slyyxp@protonmail.com",
    version="0.1.4",
    packages=find_packages(),
    install_requires=["requests==2.25.1", "mutagen==1.45.1", "loguru==0.5.3"],
    entry_points={
                'console_scripts': [
                    'rsack = rsack.main:main'
                ]
    })
