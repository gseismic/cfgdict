from setuptools import setup, find_packages


setup(
    name='cfgdict', 
    version='1.0.0', 
    packages=find_packages(),
    description='Configuration Dictionary',
    install_requires = ['loguru', 'pyyaml', 'arrow'],
    scripts=[],
    python_requires = '>=3',
    include_package_data=True,
    author='Liu Shengli',
    url='http://github.com/gseismic/cfgdict',
    zip_safe=False,
    author_email='liushengli203@163.com'
)
