from setuptools import setup, find_packages

setup(
    name='knuverse',
    version='1.0.3',
    description='A Python SDK for interfacing with KnuVerse Cloud APIs',
    long_description=open('README.md').read(),
    url='https://github.com/KnuVerse/knuverse-sdk-python',
    author='KnuVerse',
    author_email='support@knuverse.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='api sdk knuverse cloud voice authentication audiopin audiopass',

    install_requires=['requests'],
    packages=find_packages(exclude=['examples'])
)