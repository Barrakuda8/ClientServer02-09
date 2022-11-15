from setuptools import setup, find_packages

setup(name="barrakuda_messenger_client",
      version="0.1.0",
      description="barrakuda_messenger_client",
      author="barrakuda8",
      author_email="brpslelush@gmail.com",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex']
      )
