# -*- coding: utf-8 -*-
# Create Date: 2024/07/11
# Author: wangtao <wangtao.cpu@gmail.com>
# File Name: coursekg/llm/__init__.py
# Description: 大模型接口

from .prompt import IEPrompt, ExamplePrompt
from .llm import LLM, VLLM, QwenAPI
from .mllm import MiniCPM, MLLM
from .visual_prompt import MiniCPMPrompt, Interaction, VisualPrompt
from .prompt_strategy import ExamplePromptStrategy, SentenceEmbeddingStrategy
from .config import VisualConfig, LLMConfig
