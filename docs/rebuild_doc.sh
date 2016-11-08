#!/bin/bash


pushd "$(dirname "$0")"
make clean
sphinx-apidoc -f -o source/ ../knuverse
make html
popd
