# -*- coding: utf-8 -*-
# Create Date: 2024/07/11
# Author: wangtao <wangtao.cpu@gmail.com>
# File Name: coursekg/llm/prompt.py
# Description: 定义提示词类

from abc import ABC, abstractmethod
import json
import re
from loguru import logger
from glob import glob
import json
import numpy as np
from .prompt_strategy import ExamplePromptStrategy

entities = {"知识点": "知识点实体类型表示特定领域或学科中的知识单元"}
relations = {
    "包含": "某一个知识点包含另一个知识点",
    "相关": "知识点之间存在相互联系、相互影响和相互作用",
    "顺序": "学习知识点具有明显的先后关系，也就是学习某一个知识点后才能学习另一个，存在前驱后继的关系"
}
attributes = {"定义": "清楚的规定出知识点概念、意义的描述语句"}


class Prompt(ABC):

    def __init__(self) -> None:
        """ 提示词类, 包含获取提示词和格式化模型返回两类方法
        """
        pass

    @abstractmethod
    def get_ner_prompt(self, content: str) -> str:
        """ 获取实体抽取提示词

        Args:
            content (str): 待抽取的文本内容

        Raises:
            NotImplementedError: 子类需要实现该方法

        Returns:
            str: 组合后的提示词
        """
        raise NotImplementedError

    @abstractmethod
    def get_re_prompt(self, content: str, entities: list[str]) -> str:
        """ 获取关系抽取的提示词

        Args:
            content (str): 待抽取的文本内容
            entities: (list[str]): 实体列表

        Raises:
            NotImplementedError: 子类需要实现该方法

        Returns:
            str: 组合后的提示词
        """
        raise NotImplementedError

    @abstractmethod
    def get_ae_prompt(self, content: str, entities: list[str]) -> str:
        """ 获取属性抽取的提示词

        Args:
            content (str): 待抽取的文本内容
            entities: (list[str]): 实体列表

        Raises:
            NotImplementedError: 子类需要实现该方法

        Returns:
            str: 组合后的提示词
        """
        raise NotImplementedError

    @abstractmethod
    def get_best_attr(self, entity: str, attr: str, values: list[str]) -> str:
        """ 要求模型为实体的属性选择一个最佳的值

        Args:
            entity (str): 实体名称
            attr (str): 属性
            values (list[str]): 属性值列表为

        Raises:
            NotImplementedError: 子类需要实现该方法

        Returns:
            str: 组合后的提示词
        """
        raise NotImplementedError

    @abstractmethod
    def post_process(self, response: str) -> list | dict:
        """ 将模型返回处理成列表或字典格式

        Args:
            response (str): 模型输出

        Raises:
            NotImplementedError: 子类需要实现该方法

        Returns:
            list | dict: 格式输出
        """
        raise NotImplementedError


class ExamplePrompt(Prompt):

    def __init__(self, strategy: ExamplePromptStrategy) -> None:
        """ 获取提取提示词, 使用多种提示词优化, 包括CoT、基于动态检索的ICL

        Args:
            strategy (PromptExampleStrategy): 提示词检索策略
        """
        super().__init__()

        self.strategy = strategy

    def get_ner_prompt(self, content: str) -> str:
        """ 获取实体抽取提示词

        Args:
            content (str): 待抽取的文本内容

        Returns:
            str: 组合后的提示词
        """

        prompt = {
            "instruction":
            "你是专门进行实体抽取的专家。请对input的内容进行总结根据总结从中抽取出符合schema类型的实体。最后请给出你的总结和抽取到的实体列表，返回的格式为 ```json\n[\"entity1\", \"entity2\"]\n```",
            "schema": entities,
            "examples": self.strategy.get_ner_example(content),
            'input': content
        }
        return json.dumps(prompt, indent=4, ensure_ascii=False)

    def get_re_prompt(self, content: str, entities: list[str]) -> str:
        """ 获取关系抽取的提示词

        Args:
            content (str): 待抽取的文本内容
            entities: (list[str]): 实体列表

        Returns:
            str: 组合后的提示词
        """
        prompt = {
            "instruction":
            "你是专门进行关系判别的专家，请对输入的实体列表根据已有文本片段判断两两之间的关系，如果两两之间无关系或关系不在所指定的关系范围relations中，则不返回。头尾实体不应该相同。返回的格式为 ```json\n[{\"head\": \"\", \"relation\": \"\", \"tail\": \"\"}]\n```",
            "relations": relations,
            "examples": self.strategy.get_re_example(content),
            "input": f"实体列表为: {entities}, 文本片段为: '{content}'"
        }
        return json.dumps(prompt, indent=4, ensure_ascii=False)

    def get_ae_prompt(self, content: str, entities: list[str]) -> str:
        """ 获取属性抽取的提示词

        Args:
            content (str): 待抽取的文本内容
            entities: (list[str]): 实体列表

        Returns:
            str: 组合后的提示词
        """
        prompt = {
            "instruction":
            "你是专门进行属性抽取的专家，请对输入的实体列表根据已有文本片段各自抽取他们的属性值。属性范围只能来源于提供的attributes，属性值无需完全重复原文，可以是你根据原文进行的总结，如果实体没有能够总结的属性值则不返回。返回格式为 ```json\n{\"entity1\": {\"attribute1\":\"value\"}}\n```",
            "attributes":
            attributes,
            "examples": [{
                "input":
                """实体列表为: ['最优化', '随机梯度下降法'], 文本片段为: 神经网络的学习的目的是找到使损失函数的值尽可能小的参数。这是寻找最优参数的问题，解决这个问题的过程称为最优化（optimization）。遗憾的是，神经网络的最优化问题非常难。这是因为参数空间非常复杂，无法轻易找到最优解（无法使用那种通过解数学式一下子就求得最小值的方法）。
                       而且，在深度神经网络中，参数的数量非常庞大，导致最优化问题更加复杂。在前几章中，为了找到最优参数，我们将参数的梯度（导数）作为了线索。使用参数的梯度，沿梯度方向更新参数，并重复这个步骤多次，从而逐渐靠近最优参数，这个过程称为随机梯度下降法（stochastic gradient descent），
                       简称SGD。SGD是一个简单的方法，不过比起胡乱地搜索参数空间，也算是“聪明”的方法。但是，根据不同的问题，也存在比SGD更加聪明的方法。本节我们将指出SGD的缺点，并介绍SGD以外的其他最优化方法。""",
                "output":
                "```json\n{\"最优化\": {\"定义\":\"寻找神经网络最优参数的过程\"}, \"随机梯度下降法\": {\"定义\":\"使用参数的梯度，沿梯度方向更新参数，并重复这个步骤多次，从而逐渐靠近最优参数\"}}\n```"
            }],
            "input":
            f"实体列表为: {entities}, 文本片段为: '{content}'"
        }
        return json.dumps(prompt, indent=4, ensure_ascii=False)

    def get_best_attr(self, entity: str, attr: str, values: list[str]) -> str:
        """ 要求模型为实体的属性选择一个最佳的值

        Args:
            entity (str): 实体名称
            attr (str): 属性
            values (list[str]): 属性值列表为

        Returns:
            str: 组合后的提示词
        """
        prompt = {
            "instruction":
            "你是专门进行属性判别的专家，请从实体的属性对应的值列表中选择一个最佳的值，返回其下标。下标从0开始。只需要返回一个数字即可。",
            "examples": [{
                "input": """实体为: 'Numpy', 属性为: '定义', 属性值列表为: [
                'NumPy提供了许多用于操作多维数组的便捷方法，常与Python一起用于数据分析和科学计算。', 
                'NumPy是一个用于Python编程语言的科学计算库，它提供了强大的N维数组对象，以及大量的数学函数来操作这些数组。',
                '用于数值计算的库，提供了很多高级的数学算法和便利的数组（矩阵）操作方法'
                ]""",
                "output": "1"
            }],
            "input":
            f"实体为: '{entity}', 属性为: '{attr}', 属性值列表为: {values}"
        }
        return json.dumps(prompt, indent=4, ensure_ascii=False)

    def post_process(self, response: str) -> list | dict:
        """ 将模型返回处理成列表或字典格式

        Args:
            response (str): 模型输出

        Returns:
            list | dict: 格式输出
        """
        replace_tuple = [('\\', ''), ('“', '"'), ('”', '"')]  # 替换掉可能出现的非法字符
        fragments = re.findall(r'```.*?\n([\s\S]*?)\n?```', response)
        if len(fragments) > 0:
            fragment: str = fragments[-1]  # 可能会返回多个结果从语义上只取最后一个结果
            for a, b in replace_tuple:
                fragment = fragment.replace(a, b)
            try:
                res = json.loads(fragment)
                return res
            except json.decoder.JSONDecodeError as e:
                logger.error(str(e) + ' ' + fragment)
                return {}
        else:
            return {}