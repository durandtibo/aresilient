# Get Started

It is highly recommended to install in
a [virtual environment](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)
to keep your system in order.

## Installing with `uv` (recommended)

The following command installs the latest stable version of the library:

```shell
uv pip install aresilient
```

To install the latest development version from GitHub:

```shell
uv pip install git+https://github.com/durandtibo/aresilient.git
```

To install a specific version:

```shell
uv pip install aresilient==0.3.0
```

## Installing with `pip`

The following command installs the latest stable version of the library:

```shell
pip install aresilient
```

To install the latest development version from GitHub:

```shell
pip install git+https://github.com/durandtibo/aresilient.git
```

To install a specific version:

```shell
pip install aresilient==0.3.0
```

## Verifying Installation

After installation, you can verify that aresilient is correctly installed by running:

```shell
python -c "import aresilient; print(aresilient.__version__)"
```

Or try a simple example:

```python
from aresilient import get_with_automatic_retry

# Make a simple GET request (this is a safe example that won't actually execute)
# response = get_with_automatic_retry("https://api.example.com/data")
# print(response.json())

# Verify the module is properly imported
print("aresilient imported successfully!")
```

### Testing Async Support

To verify async support is working:

```python
import asyncio
from aresilient import get_with_automatic_retry_async


async def test_async():
    print("Async support is working!")
    return True


result = asyncio.run(test_async())
print(f"Test result: {result}")
```

## Installing from source

To install `aresilient` from source, you can follow the steps below.

### Prerequisites

This project uses [`uv`](https://docs.astral.sh/uv/) for dependency management. Please refer to
the [uv installation documentation](https://docs.astral.sh/uv/getting-started/installation/) for
installation instructions.

### Clone the Repository

```shell
git clone git@github.com:durandtibo/aresilient.git
cd aresilient
```

### Create a Virtual Environment

It is recommended to create a Python 3.10+ virtual environment:

```shell
make setup-venv
```

This command creates a virtual environment using `uv` and installs all dependencies including
development tools.

Alternatively, you can create a conda virtual environment:

```shell
make conda
conda activate aresilient
make install
```

### Install Dependencies

To install only the core dependencies:

```shell
make install
```

To install all dependencies including documentation tools:

```shell
make install-all
```

### Verify Installation

You can test the installation with the following command:

```shell
make unit-test-cov
```

This will run the test suite with coverage reporting.

## Development Setup

If you plan to contribute to aresilient, please also install the development tools.

Using `uv`:

```shell
uv pip install -e ".[dev,docs]"
```

Using `pip`:

```shell
pip install -e ".[dev,docs]"
```

Then install the pre-commit hooks:

```shell
pre-commit install
```

See [CONTRIBUTING.md](https://github.com/durandtibo/aresilient/blob/main/.github/CONTRIBUTING.md)
for
more information about contributing.
