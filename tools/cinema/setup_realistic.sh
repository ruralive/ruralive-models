#!/bin/bash
# Everything tools/cinema/real.py needs, on a fresh Linux machine or cloud session:
#   Blender as a Python module, MPFB 2 (GPL code, CC0 assets) and the MakeHuman CC0 system assets.
# Network: pypi, github.com and files.makehumancommunity.org.
set -eu
python3 -c "import bpy" 2>/dev/null || pip install bpy==5.3.0
mkdir -p /opt/chars
if [ ! -d /opt/chars/mpfb2 ]; then
  git clone https://github.com/makehumancommunity/mpfb2 /opt/chars/mpfb2
  git -C /opt/chars/mpfb2 checkout 6ff1eb358f6c1959ced77e79e6dd2406d9a71f49
fi
if [ ! -d /opt/chars/mh/data ]; then
  mkdir -p /opt/chars/mh
  curl -fsSL -o /opt/chars/mh/assets.zip \
    https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip
  python3 -c "import zipfile;zipfile.ZipFile('/opt/chars/mh/assets.zip').extractall('/opt/chars/mh/data')"
fi
echo "ready: python3 tools/cinema/real.py <out> <shots> tomas amara mei beggar"
