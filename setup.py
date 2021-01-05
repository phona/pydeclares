import setuptools

from pydeclares import version

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='pydeclares',
    version=version,
    author="heweitao",
    author_email="675428202@qq.com",
    description="A tool for provide format and serialize support to json, xml, form data and query string.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/phona/pydeclares",
    packages=setuptools.find_packages(),
    extras_require={
        'typing_extensions': ['typing-extensions>=3.7.2'],
    },
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
