# -*- coding: utf-8 -*-
# Create Date: 2024/07/11
# Author: wangtao <wangtao.cpu@gmail.com>
# File Name: course_graph/llm/__init__.py
# Description: 大模型接口

from .ontology import ONTOLOGY
from .llm import LLM, VLLM, Qwen, Ollama, OpenAI
from .config import LLM_CONFIG, VLM_CONFIG
from .type import Database
from .vlm import VLM
