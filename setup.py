from setuptools import setup, find_packages

setup(
    name='core-service',
    version='0.1.0',
    url='https://github.com/sarafanio/core-service.git',
    author='Sarafan Community',
    author_email='flu2020@pm.me',
    description='asyncio service microframework',
    packages=find_packages(),
    install_requires=[
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-asyncio',
            'pytest-cov',
            'pylama',
            'mypy',
            'Sphinx',
        ]
    }
)
