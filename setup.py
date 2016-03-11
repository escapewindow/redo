try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name="redo",
    version="1.5",
    description="Utilities to retry Python callables.",
    author="Ben Hearsum",
    author_email="ben@hearsum.ca",
    packages=["redo"],
    entry_points={
        "console_scripts": ["retry = redo.cmd:main"],
    },
    url="https://github.com/bhearsum/redo",
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: PyPy",
    ]
)
