# -*- coding: utf-8 -*-
# Create Date: 2024/07/11
# Author: wangtao <wangtao.cpu@gmail.com>
# File Name: course_graph/llm/vl_prompt.py
# Description: 定义图文理解模型提示词类

from typing import Literal
from PIL import Image
import os
import json
import random


def get_content(image_paths, question) -> list:
    if len(image_paths) == 0:
        content = []
    elif isinstance(image_paths, str):
        content = [Image.open(image_paths).convert('RGB')]
    else:
        content = [Image.open(path).convert('RGB') for path in image_paths]
    content.append(question)
    return content


class MultiImagePrompt:

    def __init__(self) -> None:
        """ 支持多轮对话 / 多图对话
        """
        super().__init__()
        self.messages: list[dict] = []

    def get_ocr_prompt(self, image_paths: str | list[str]) -> tuple[list, str]:
        """ OCR 提示词

        image_paths (str | list): 图片或图片路径

        Returns:
            tuple[str, str]: 组合后的历史记录, 指令
        """
        prompt = """将图片中识别到的文字转换文本输出。你必须做到：
        1. 你的回答中严禁包含 “以下是根据图片内容生成的文本：”或者 “ 将图片中识别到的文字转换文本格式输出如下：” 等这样的提示语。
        2. 不需要对内容进行解释和总结。
        3. 代码包含在``` ```中、段落公式使用 $$ $$ 的形式、行内公式使用 $ $ 的形式。
        4. 如果图片中包含图表，对图表形成摘要即可，无需添加例如“图片中的文本内容如下：”等这样的提示语。
        再次强调，不要输出和识别到的内容无关的文字。"""
        instruction = '你是一个OCR模型。'
        messages = self.messages + get_content(image_paths, prompt)
        return messages, instruction

    def get_ie_prompt(self, image_paths: str | list[str]) -> tuple[list, str]:
        """ 信息提取提示词

        image_paths (str | list): 图片或图片路径

        Returns:
            tuple[str, str]: 组合后的历史记录, 指令
        """
        prompt = '请帮我提取图片中的主要内容'
        instruction = '你是一个能够总结图片内容的模型。'
        messages = self.messages + get_content(image_paths, prompt)
        return messages, instruction

    def get_catalogue_prompt(self,
                             image_paths: str | list[str]) -> tuple[list, str]:
        """ 目录识别提示词

        image_paths (str | list): 图片或图片路径

        Returns:
            tuple[str, str]: 组合后的历史记录, 指令
        """
        prompt = """给你一张图片，他是书籍中的某一页。请你帮我判断这一页是不是这本书的目录页中的其中一页。你必须做到：
        1.只需要回答我是或否这一个字即可。不需要其他任何的解释。
        2.书籍的目录页是指包含一些章节名称和对应的页码。书籍的封面、作者介绍、版权页、前言和正文等都不能算作目录页。"""
        instruction = '你是一个能够总结图片内容的模型。'
        messages = self.messages + get_content(image_paths, prompt)
        return messages, instruction

    def get_context_ie_prompt(
            self, message: str,
            image_paths: str | list[str]) -> tuple[list, str]:
        """ 带有上文信息的信息提取提示词

        message (str): 上下文信息
        image_paths (str | list): 图片或图片路径

        Returns:
            tuple[str, str]: 组合后的历史记录, 指令
        """
        prompt = f'''第一张图片的主要内容是：{message},
        第一张图片和第二张图片在文档中是顺序出现的，请你据此帮我总结第二张图片的主要内容'''
        instruction = '你是一个能够总结图片内容的模型。'
        messages = self.messages + get_content(image_paths, prompt)
        return messages, instruction

    def use_examples(
        self,
        type_: Literal['ocr', 'ie', 'catalogue', 'content_ie'],
        example_dataset_path: str = 'dataset/image_example'
    ) -> 'MultiImagePrompt':
        """ 添加示例

        Args:
            type_ (Literal['ocr', 'ie', 'catalogue', 'content_ie']): 示例类型.
            example_dataset_path (str, optional): 使用多模态模型上下文学习源数据地址文件夹. Defaults to 'dataset/image_example'.
        """
        examples = []
        with open(os.path.join(example_dataset_path, 'example.json')) as f:
            lines = json.load(f)
            for line in lines:
                if line['type'] == type_:
                    examples.append({
                        'image_path': line['image'],
                        'question': line['input'],
                        'answer': line['output']
                    })
        if len(examples) > 5:
            examples = random.sample(examples, 5)

        for example in examples:
            self.messages.append({
                'role':
                'user',
                'content':
                get_content(example['image_paths'], example['question'])
            })
            self.messages.append({
                'role': 'assistant',
                'content': [example['answer']]
            })

        return self