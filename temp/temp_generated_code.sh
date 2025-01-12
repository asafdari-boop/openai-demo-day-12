#!/bin/bash

if [ -d "$HOME/cap" ]; then
  rm -rf "$HOME/cap"
  echo "Directory ~/cap deleted successfully."
else
  echo "Directory ~/cap does not exist."
fi