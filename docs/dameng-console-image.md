# Dameng console image build

The normal `Dockerfile` contains both MySQL and Dameng dependencies. Runtime
selection remains `DB_TYPE=mysql` by default and `DB_TYPE=dm` for Dameng; there
is no `Dockerfile.dm` and no special Console image route.

## Private driver context

The Console receives the official driver through the named `dameng` build
context. Its relevant layout is:

```text
python/
  dpi/
    libdmdpi.so
    dependencies/
    include/
  drivers/python/
    dmPython/
    dmDjango/dmDjango3.0/
```

On a machine with an installed DM8 instance, a local context can be prepared
without copying the complete installation include tree:

```bash
bash scripts/prepare_dameng_python_driver.sh <DM_INSTALLATION_ROOT>
```

The normal Dockerfile compiles dmPython using `DM_HOME/dpi/include`, installs
dmDjango, then removes source and headers from the builder. The final image
retains only the DPI library and its runtime dependencies. Driver material is
excluded from Git and must be architecture-compatible with the target image.
