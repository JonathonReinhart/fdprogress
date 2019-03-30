from setuptools import setup
import os

def read_project_file(path):
    proj_dir = os.path.dirname(__file__)
    path = os.path.join(proj_dir, path)
    with open(path, 'r') as f:
        return f.read()

setup(
    name = 'fdprogress',
    version = '0.2.0',
    description = 'Monitor file descriptor progress on Linux',
    long_description = read_project_file('README.md'),
    long_description_content_type = 'text/markdown',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Topic :: System :: Monitoring',
    ],
    license = 'MIT',
    keywords = 'file descriptor watch',
    author = 'Jonathon Reinhart',
    author_email = 'jonathon.reinhart@gmail.com',
    url = 'https://github.com/JonathonReinhart/fdprogress',
    py_modules = ['fdprogress'],
    entry_points = {
        'console_scripts': [
            'fdprogress = fdprogress:main',
        ]
    },
)
