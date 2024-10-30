# -*- coding: utf-8 -*-
# Create Date: 2024/10/25
# Author: wangtao <wangtao.cpu@gmail.com>
# File Name: course_graph/parser/pdf_parser/structure_model.py
# Description: 布局分析模型封装

from abc import ABC, abstractmethod
from typing_extensions import Literal, Required, TypedDict
from numpy import ndarray
from paddleocr.ppstructure.recovery.recovery_to_doc import sorted_layout_boxes
from paddleocr import PPStructure
from doclayout_yolo import YOLOv10
import json
from course_graph_ext import post_process


class StructureResult(TypedDict, total=False):
    type: Required[str]
    bbox: Required[tuple[float]]
    text: str


class StructureModel(ABC):

    @abstractmethod
    def predict(self, img: ndarray) -> list[StructureResult]:
        """ 生成布局分析结果

        Args:
            img (ndarray): 图像数组

        Returns:
            list[StructureResult]: 布局分析结果
        """
        raise NotImplementedError

    def __call__(self, img: ndarray) -> list[StructureResult]:
        return self.predict(img)


class PaddleStructure(StructureModel):

    def __init__(self) -> None:
        """ 飞桨布局分析模型 ref: https://github.com/PaddlePaddle/PaddleOCR/
        """
        super().__init__()
        self.pp = PPStructure(table=False, ocr=True, show_log=False)

    def predict(self, img: ndarray) -> list[StructureResult]:
        result = self.pp(img)
        h, w, _ = img.shape
        res = sorted_layout_boxes(result, w)
        return [{
            'type': item['type'],
            'bbox': tuple(item['bbox'])
        } for item in res]


class LayoutYOLO(StructureModel):

    def __init__(self, model_path: str, device: str = 'cuda') -> None:
        """ DocLayout-YOLO 布局分析模型 ref: https://github.com/opendatalab/DocLayout-YOLO/blob/main/README-zh_CN.md

        Args:
            model_path (str): 模型路径
            device (str, optional): 运行设备. Defaults to 'cuda'.
        """
        super().__init__()
        self.model = YOLOv10(model_path)
        self.device = device

    def predict(self, img: ndarray) -> list[StructureResult]:
        result = json.loads(
            self.model.predict(img,
                               imgsz=1024,
                               conf=0.2,
                               verbose=False,
                               device=self.device)[0].tojson())
        result = [item for item in result if item['name'] != 'abandon']
        # 将 bbox 坐标变换为 (x1,y1,x2,y2)
        for item in result:
            item['bbox'] = (item['box']['x1'], item['box']['y1'],
                            item['box']['x2'], item['box']['y2'])
        h, w, _ = img.shape
        res = sorted_layout_boxes(result, w)

        # 后处理 (接受元组类型)
        res = post_process(detections=[(item['name'], item['bbox'])
                                       for item in res],
                           iou_threshold=0.1)

        return [
            {
                'type': item[0].replace('plain text', 'text'),  # 替换标准写法
                'bbox': item[1]
            } for item in res
        ]