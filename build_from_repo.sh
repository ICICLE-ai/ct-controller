#!/bin/bash
if [[ -z "$BRANCH" ]]; then 
  pip install git+https://github.com/ICICLE-ai/ct-controller
else
  pip install git+https://github.com/ICICLE-ai/ct-controller@${BRANCH};
fi
