from setuptools import setup, find_packages

setup(name="asobann",
      packages=find_packages(where="src"),
      package_dir={"": "src"},
      )
