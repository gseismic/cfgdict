import re
import json
import yaml
import os
import arrow
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from copy import deepcopy
from loguru import logger as default_logger
from .utils import flatten_dict, resolve_value
from .schema import Field, Schema
from .exception import FieldValidationError, FieldKeyError


class ConfigV2:
    
       def __init__(self, 
                 config_dict: Optional[Dict[str, Any]] = None, 
                 schema: Optional[List[Dict[str, Any]]] = None, 
                 strict: bool = False, 
                 verbose: bool = False, 
                 logger: Optional[Any] = None):
        self._config = config_dict or {}
        self._schema = Schema.make_schema(schema)
        self._strict = strict or False
        self._verbose = verbose or False
        self._logger = logger or default_logger