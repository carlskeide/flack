from setuptools import setup

__version__ = "1.2.0"
__url__ = "https://github.com/carlskeide/flack"

setup(
    name="flack",
    version=__version__,
    description="Slack integration for flask",
    author="Carl Skeide",
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
