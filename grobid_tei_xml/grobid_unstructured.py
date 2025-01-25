"""
Helper functions to parse an unstructured citation string using GROBID, then
fuzzy match using the result.

- try to parse string with GROBID REST API call
- transform the GROBID XML response to a simple dict/struct

TODO: more general versions which handle multiple reference strings in a batch?
"""

import io
import sys
import xml.etree.ElementTree as ET
from typing import Optional

from .parse import biblio_info
