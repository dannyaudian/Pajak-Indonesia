from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in pajak_indonesia/__init__.py
from pajak_indonesia import __version__ as version

setup(
    name="pajak_indonesia",
    version=version,
    description="Indonesian Tax Management App",
    author="Your Organization",
    author_email="your@email.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)