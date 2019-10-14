import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='pydeclares',
    version='0.3',
    author="heweitao",
    author_email="675428202@qq.com",
    description="A tool for provide format and serialize support to json, xml, form data and query string.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/phona/pydeclares",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
