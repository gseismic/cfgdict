import os
from setuptools import setup, find_packages


about = {}
here = os.path.abspath(os.path.dirname(__file__))
print(here)
with open(os.path.join(here, "cfgdict", "version.py"), "r") as f:
    exec(f.read(), about)

with open("README.md", "r") as f:
    readme = f.read()

test_requirements = [
    "pytest>=3"
]

setup(
    name=about['__title__'],
    version=about['__version__'],
    packages=find_packages(),
    description=about['__description__'], 
    install_requires = ['loguru', 'pyyaml', 'arrow'],
    scripts=[],
    python_requires = '>=3',
    include_package_data=True,
    long_description=readme,
    long_description_content_type="text/markdown",
    author=about['__author__'],
    url='http://github.com/gseismic/cfgdict',
    classifiers=[
        
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        'License :: OSI Approved :: MIT License',  
        "Natural Language :: English",

        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        "Programming Language :: Python :: Implementation :: PyPy",
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities'
    ],
    zip_safe=False,
    tests_require=test_requirements,
    author_email='liushengli203@163.com',
    project_urls={
        "Source": "https://github.com/gseismic/cfgdict",
    },
)
