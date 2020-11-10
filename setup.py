from setuptools import setup
from pathlib import Path

__version__ = "1.3.5"
__url__ = "https://github.com/carlskeide/flack"

with open(Path.cwd() / "README.md", "r") as f:
    long_description = f.read()


setup(
    name="flack",
    version=__version__,
    description="Slack integration for flask",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Carl Skeide",
    author_email="carl@skeide.se",
    license="MIT",
    keywords=[
        "flask",
        "slack"
    ],
    classifiers=[],
    packages=["flack"],
    include_package_data=True,
    zip_safe=False,
    url=__url__,
    download_url="{}/archive/{}.tar.gz".format(__url__, __version__),
    install_requires=[
        "flask",
        "requests"
    ]
)
