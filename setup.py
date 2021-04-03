from setuptools import setup

setup(
    name='ControlDeck',
    py_modules=['controldeck'],
    entry_points={
    'console_scripts': ['controldeck = controldeck:main', ],},
)
