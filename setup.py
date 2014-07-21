from setuptools import setup, find_packages

source_path = 'src'
packages = find_packages(source_path)

setup(name='qao',
      version='1.0',
      packages=packages,
      package_dir={'': source_path},
     )
