# from distutils.core import setup
from setuptools import setup, find_packages

setup(name='seaeye',
      version='0.1',
      description='silly programming language',
      author='William Bettridge-Radford',
      author_email='william.bettridge.radford@gmail.com',
      packages=find_packages(include=['seaeye']),
      )
