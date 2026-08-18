# Dameng console image build

The normal console image build is unchanged. Dameng uses the separate
`Dockerfile.dm` entry point and receives official driver files through a named
Docker build context. The normal Docker build context excludes those files.

## Prepare the private driver bundle

On a machine with the matching Dameng installation, run:

```bash
./scripts/prepare_dameng_python_driver.sh /path/to/dmdbms
```

The script reads the official `dmPython`, `dmDjango3.0`, and `libdmdpi.so`
artifacts and creates this ignored layout:

```text
third_party/dameng/
├── bin/libdmdpi.so
└── drivers/python/
    ├── dmPython/
    └── dmDjango/dmDjango3.0/
```

This DM_HOME-compatible bundle is intentionally excluded from Git and from the
normal Docker context. It is copied from the named `dameng` context into the
DM builder only, installed into the virtual environment with `DM_HOME` and
`PATH` set, and removed before the final image is assembled. The final image
retains only the installed Python packages and native runtime library.

## Build

```bash
docker buildx build \
  --file Dockerfile.dm \
  --build-context dameng=third_party/dameng \
  --tag rainbond/rainbond-console:dm-test \
  --load .
```

For a regular MySQL or SQLite image, continue to use `Dockerfile`; it neither
sends nor installs a Dameng artifact. The Dameng build requires an
architecture- and operating-system-compatible official driver bundle. No
database connection credentials belong in the image or build arguments.
