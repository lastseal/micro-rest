from setuptools import setup

setup(
    name="micro-rest",
    version="1.0.0",
    description="Módulo que permite crear micro servicios REST/API",
    author="Rodrigo Arriaza",
    author_email="hello@lastseal.com",
    url="https://www.lastseal.com",
    packages=['micro'],
    install_requires=[ 
        i.strip() for i in open("requirements.txt").readlines() 
    ]
)
