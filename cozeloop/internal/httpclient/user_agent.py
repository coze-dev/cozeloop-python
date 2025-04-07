# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import platform
import json
import os
from typing import Dict

from cozeloop import internal

# User agent components
USER_AGENT_SDK = "cozeloop-python"
USER_AGENT_LANG = "python"
USER_AGENT_LANG_VERSION = platform.python_version()
USER_AGENT_OS_NAME = platform.system().lower()
USER_AGENT_OS_VERSION = os.getenv("OSVERSION", "unknown")
SCENE = "cozeloop"
SOURCE = "openapi"

USER_AGENT = f"{USER_AGENT_SDK}/{internal.__version__} {USER_AGENT_LANG}/{USER_AGENT_LANG_VERSION} {USER_AGENT_OS_NAME}/{USER_AGENT_OS_VERSION}"
CLIENT_USER_AGENT = json.dumps(
    {
        "version": internal.__version__,
        "lang": USER_AGENT_LANG,
        "lang_version": USER_AGENT_LANG_VERSION,
        "os_name": USER_AGENT_OS_NAME,
        "os_version": USER_AGENT_OS_VERSION,
        "scene": SCENE,
        "source": SOURCE,
    }
)


def user_agent_header() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "X-Coze-Client-User-Agent": CLIENT_USER_AGENT,
    }
