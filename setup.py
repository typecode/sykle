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
    install_requires=[
        'docopt>=0.6.2,<0.7',
        'python-dotenv>=0.9.1,<0.10'
    ],
    entry_points={
        'console_scripts': [
            'syk=src.cli:main',
        ]
    },
)
