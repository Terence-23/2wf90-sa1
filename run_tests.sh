#!/bin/bash

find . -maxdepth 1 -type f -iname '*test*.py' -exec python {} \;
