from distutils.core import setup

setup(
    name = 'aps-gsd',
    version = '0.1dev',
    packages=['gsd', 'gsd.test'],
    scripts=['bin/gsd.py'],
    license='LICENSE.txt',
    description='APS - Common Service Daemon',
    long_description=open('README.txt').read(),
    install_requires=[
        "pyzmq >= 2.1.7"
    ],
)

