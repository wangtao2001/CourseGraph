# -*- coding: utf-8 -*-
# Create Date: 2024/09/20
# Author: wangtao <wangtao.cpu@gmail.com>
# File Name: course_graph/llm/llm.py
# Description: 定义兼容 openAI API 的大模型类

import openai
from openai.types.chat import *
from openai import NOT_GIVEN, NotGiven
from abc import ABC
from .config import LLM_CONFIG
import os
import requests
import subprocess
import time
import shlex
import ollama


class LLM(ABC):

    def __init__(
        self,
    ) -> None:
        """ 大模型抽象类
        """
        ABC.__init__(self)

        self.model: str | None = None  # 需要在子类中额外初始化
        self.client: openai.OpenAI | None = None

        self.json: bool = False
        self.stop = None
        self.instruction = 'You are a helpful assistant.'

    def chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam
        | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN
    ) -> ChatCompletionMessage:
        """ 基于message中保存的历史消息进行对话, 请在外部保存历史记录, LLM 对象不负责保存

        Args:
            messages (list[ChatCompletionMessageParam]): 历史消息
            tools (list[ChatCompletionToolParam] | NotGiven, optional): 外部tools. Defaults to NOT_GIVEN.
            tool_choice: (ChatCompletionToolChoiceOptionParam | NotGiven, optional): 强制使用外部工具. Defaults to NOT_GIVEN.
            parallel_tool_calls: (bool | NotGiven, optional): 允许工具并行调用. Defaults to NOT_GIVEN.

        Returns:
            ChatCompletionMessage: 模型返回结果
        """
        # functions 废弃
        # 参考: https://platform.openai.com/docs/api-reference/chat/create
        messages = [{'role': 'system', 'content': self.instruction}] + messages
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            top_p=LLM_CONFIG.top_p,
            temperature=LLM_CONFIG.temperature,
            presence_penalty=LLM_CONFIG.presence_penalty,
            frequency_penalty=LLM_CONFIG.frequency_penalty,
            max_tokens=LLM_CONFIG.max_tokens,
            tools=tools,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            response_format={
                'type': 'json_object'
            } if self.json else {
                'type': 'text'
            },
            stop=self.stop,
            extra_body={
                'top_k': LLM_CONFIG.top_k
            }).choices[0].message

    def chat(self, message: str) -> str:
        """ 模型的单轮对话

        Args:
            message (str): 用户输入

        Returns:
            str | ChatCompletionMessage: 模型输出
        """
        response = self.chat_completion(messages=[{'role': 'user', 'content': message}])
        return response.content


class OpenAI(LLM):

    def __init__(self,
                 name: str,
                 *,
                 base_url: str = None,
                 api_key: str = None):
        """ OpenAI 模型 API 服务

        Args:
            name (str): 模型名称
            base_url (str, optional): 地址. Defaults to None.
            api_key (str, optional): API key. Defaults to None.
        """
        super().__init__()

        self.model = name
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
        )


class Qwen(OpenAI):

    def __init__(self,
                 name: str = 'qwen-max',
                 *,
                 api_key: str = os.getenv("DASHSCOPE_API_KEY")):
        """ Qwen 系列模型 API 服务

        Args:
            name (str, optional): 模型名称. Defaults to qwen-max.
            api_key (str, optional): API key. Defaults to os.getenv("DASHSCOPE_API_KEY").
        """
        super().__init__(
            name=name,
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            api_key=api_key)


class Serve:

    def __init__(self,
                 command_list: list[str],
                 test_url: str,
                 log: bool = True,
                 timeout: int = 30):
        """ 启动服务

        Args:
            command_list (list[str]): 命令列表
            test_url (str): 测试地址
            log (bool, optional): 输出控制台日志. Defaults to True.
            timeout (int, optional): 超时时间. Defaults to 30.

        Raises:
            TimeoutError: 服务启动超时
        """
        self.process = subprocess.Popen(
            command_list,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ) if not log else subprocess.Popen(command_list) 

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(test_url)
                if response.status_code == 200:
                    return
            except requests.ConnectionError:
                pass
            time.sleep(1)
        raise TimeoutError

    def close(self):
        """ 关闭服务
        """
        if self.process:
            self.process.terminate()
            self.process.wait()

    def __enter__(self) -> 'Serve':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


class VLLM(LLM, Serve):

    def __init__(self,
                 path: str,
                 *,
                 host: str = 'localhost',
                 port: int = 9017,
                 starting_command: str = None,
                 timeout: int = 60,
                 log: bool = True):
        """ 使用VLLM加载模型

        Args:
            path (str): 模型名称或路径
            timeout (int, optional): 启动服务超时时间. Defaults to 60.
            host (str, optional): 服务地址. Defaults to 'localhost'.
            port (int, optional): 服务端口. Defaults to 9017.
            log (bool, optional): 输出控制台日志. Defaults to True.
            starting_command (str, optional): VLLM启动命令 (适合于需要自定义template的情况), 也可以使用默认命令, LLMConfig中的配置会自动加入. Defaults to None.
        """
        LLM.__init__(self)

        self.host = host
        self.port = port

        self.model = path
        if starting_command is None:
            command_list = shlex.split(f"""vllm serve {self.model}\
                                            --host {self.host}\
                                            --port {self.port}\
                                            --gpu-memory-utilization {str(LLM_CONFIG.gpu_memory_utilization)}\
                                            --tensor-parallel-size {str(LLM_CONFIG.tensor_parallel_size)}\
                                            --max-model-len {str(LLM_CONFIG.max_model_len)}\
                                            --enable-auto-tool-choice\
                                            --tool-call-parser hermes\
                                            --disable-log-requests""")
        else:
            command_list = shlex.split(starting_command)
            if "--gpu-memory-utilization" not in command_list:
                command_list.extend([
                    "--gpu-memory-utilization",
                    str(LLM_CONFIG.gpu_memory_utilization)
                ])
            if "--tensor-parallel-size" not in command_list:
                command_list.extend([
                    "--tensor-parallel-size",
                    str(LLM_CONFIG.tensor_parallel_size)
                ])
            if "--max-model-len" not in command_list:
                command_list.extend(
                    ["--max-model-len",
                     str(LLM_CONFIG.max_model_len)])
            try:
                idx = command_list.index('--host')
                self.host = command_list[idx + 1]
            except ValueError:
                self.host = host
            try:
                idx = command_list.index('--port')
                self.port = command_list[idx + 1]
            except ValueError:
                self.port = port

        Serve.__init__(self,
                       command_list=command_list,
                       timeout=timeout,
                       log=log,
                       test_url=f'http://{self.host}:{self.port}/health')

        self.client = openai.OpenAI(
            api_key='EMPTY', base_url=f'http://{self.host}:{self.port}/v1')


class Ollama(LLM, Serve):

    def __init__(self,
                 name: str,
                 *,
                 host: str = 'localhost',
                 port: int = 9017,
                 timeout: int = 60):
        """ ollama模型服务

        Args:
            name (str): 模型名称
            timeout (int, optional): 启动服务超时时间. Defaults to 60.
            host (str, optional): 服务地址. Defaults to 'localhost'.
            port (int, optional): 服务端口. Defaults to 9017.
        """
        LLM.__init__(self)
        self.model = name

        available_models = [m['name'] for m in ollama.list()['models']]
        if name not in available_models and name:
            ollama.pull(name)

        self.host = host
        self.port = port

        Serve.__init__(self,
                       command_list=['ollama', 'serve'],
                       timeout=timeout,
                       test_url=f'http://{self.host}:{self.port}')
        self.client = openai.OpenAI(
            api_key='EMPTY',
            base_url=f'http://{self.host}:{self.port}/v1',
        )
