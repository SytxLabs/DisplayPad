from setuptools import setup


def read_requirements(file):
    with open(file) as f:
        return f.read().splitlines()


requirements = read_requirements("requirements.txt")

setup(
    name='DisplayPad.py',
    version='1.0.0',
    author='Sytxlabs',
    author_email='info@sytxlabs.eu',
    url='https://sytxlabs.eu',
    description='A simple library to for the Mountain DisplayPad.',
    license="MIT license",
    install_requires=requirements,
)