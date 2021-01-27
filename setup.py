import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="peg_leg",
    version="0.2.0",
    author="Gabriel Ionescu",
    author_email="gabe@erisian.tech",
    description="PEG parser generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/formerly-a-trickster/peg-leg",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)