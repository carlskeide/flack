from setuptools import setup

__version__ = "1.1.0"

setup(name="flack",
      version=__version__,
      description="Slack integration for flask",
      author="Carl Skeide",
      packages=['flack'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        "flask",
        "requests"
      ])
