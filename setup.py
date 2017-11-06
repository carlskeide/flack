from setuptools import setup

__version__ = "1.1.0"

setup(name="flack",
      version=__version__,
      description="Slack integration for flask",
      author="Carl Skeide",
      py_modules=["flack"],
      install_requires=[
        "flask",
        "requests"
      ])
