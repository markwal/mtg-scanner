"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib
import traceback

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

try:
    setup(
        # There are some restrictions on what makes a valid project name
        # specification here:
        # https://packaging.python.org/specifications/core-metadata/#name
        name="mtg-scanner",  # Required
        version="0.1.0",  # Required
        description="Command line tool to identify mtg cards via sheet fed scanner",  # Optional
        long_description=long_description,  # Optional
        long_description_content_type="text/markdown",  # Optional (see note above)
        url="https://github.com/markwal/mtg-scanner",  # Optional
        author="Mark Walker",  # Optional
        author_email="markwal@hotmail.com",  # Optional

        # For a list of valid classifiers, see https://pypi.org/classifiers/
        classifiers=[  # Optional
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            "Development Status :: 3 - Alpha",
            # Indicate who your project is intended for
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Build Tools",
            # Pick your license as you wish
            "License :: OSI Approved :: MIT License",
            # Specify the Python versions you support here. In particular, ensure
            # that you indicate you support Python 3. These classifiers are *not*
            # checked by 'pip install'. See instead 'python_requires' below.
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3 :: Only",
        ],

        # This field adds keywords for your project which will appear on the
        # project page. What does your project relate to?
        #
        # Note that this is a list of additional keywords, separated
        # by commas, to be used to assist searching for the distribution in a
        # larger catalog.
        # keywords="sample, setuptools, development",  # Optional

        # When your source code is in a subdirectory under the project root, e.g.
        # `src/`, it is necessary to specify the `package_dir` argument.
        # package_dir={"": "src"},  # Optional
        # You can just specify package directories manually here if your project is
        # simple. Or you can use find_packages().
        #
        # Alternatively, if you just want to distribute a single Python file, use
        # the `py_modules` argument instead as follows, which will expect a file
        # called `my_module.py` to exist:
        #
        #   py_modules=["my_module"],
        #
        packages={"mtg_scanner"},  # Required

        python_requires=">=3.7, <4",
        install_requires=["pytesseract", "numpy", "sympy", "opencv-python", "click"],  # Optional
        # List additional groups of dependencies here (e.g. development
        # dependencies). Users will be able to install these using the "extras"
        # syntax, for example:
        #
        #   $ pip install sampleproject[dev]
        #
        # Similar to `install_requires` above, these must be valid existing
        # projects.
        #extras_require={  # Optional
        #    "dev": ["check-manifest"],
        #    "test": ["coverage"],
        #},
        # If there are data files included in your packages that need to be
        # installed, specify them here.
        package_data={  # Optional
        # REVIEW markwal: add the tesseract english data here?
        #    "sample": ["package_data.dat"],
        },
        # Although 'package_data' is the preferred approach, in some case you may
        # need to place data files outside of your packages. See:
        # http://docs.python.org/distutils/setupscript.html#installing-additional-files
        #
        # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
        #data_files=[("my_data", ["data/data_file"])],  # Optional
        # To provide executable scripts, use entry points in preference to the
        # "scripts" keyword. Entry points provide cross-platform support and allow
        # `pip` to create the appropriate form of executable for the target
        # platform.
        #
        # For example, the following would provide a command called `sample` which
        # executes the function `main` from this package when invoked:
        entry_points={  # Optional
            "console_scripts": [
                "mtg-scan=mtg_scanner:main",
            ],
        },
        # List additional URLs that are relevant to your project as a dict.
        #
        # This field corresponds to the "Project-URL" metadata fields:
        # https://packaging.python.org/specifications/core-metadata/#project-url-multiple-use
        #
        # Examples listed include a pattern for specifying where the package tracks
        # issues, where the source is hosted, where to say thanks to the package
        # maintainers, and where to support the project financially. The key is
        # what's used to render the link text on PyPI.
        project_urls={  # Optional
            "Bug Reports": "https://github.com/markwal/mtg-scanner/issues",
#        "Funding": "https://donate.pypi.org",
#        "Say Thanks!": "http://saythanks.io/to/example",
            "Source": "https://github.com/markwal/mtg-scanner/",
        },
    )
except:
    traceback.print_exc()
