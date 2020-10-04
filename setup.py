import setuptools
import os

here = os.path.abspath(os.path.dirname(__file__))

version_path = os.path.join(here, 'terminalplot', 'version.py')
with open(version_path, encoding='utf-8') as f:
    exec(f.read())

with open("README.md", "r") as fh:
    long_description = fh.read()

def version():
    if os.getenv('TRAVIS_BUILD_STAGE_NAME', '') == 'Deploy test':
        return __version__ + '.' + os.getenv('TRAVIS_BUILD_NUMBER', '')
    else:
        return __version__

setuptools.setup(
    name="zmf-cli",
    version=version(),
    author="Michael Kressibucher",
    author_email="michael.kressibucher@gmail.com",
    description="Command line wrapper for ChangeMan ZMF Rest API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kressi/zmf-cli",
    packages=setuptools.find_packages(),
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    zip_safe=True,
    entry_pointes={
        "console_script": ["zmf = zmf-cli.zmf:main"]
    }
)
