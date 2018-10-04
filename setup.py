from setuptools import setup
from src import __version__

setup(
    name='sykle',
    version=__version__,
    description='Rake like docker-compose coordinator',
    author='Type/Code',
    author_email='eric@typecode.com',
    classifier=[
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: Public Domain',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.4',
    ],
    packages=['src', 'plugins.sync_pg_data'],
    install_requires=['docopt', 'python-dotenv', 'boto3>=1.7.57,<1.8'],
    entry_points={
        'console_scripts': [
            'syk=src.cli:main',
        ]
    },
)
