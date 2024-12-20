# -*- coding: utf-8 -*-
# Create Date: 2024/07/11
# Author: wangtao <wangtao.cpu@gmail.com>
# File Name: course_graph/parser/__init__.py
# Description: 文档解析器接口

from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .document import Document
from .type import BookMark
from .parser import Parser
from .type import Page
from .config import config
from .utils import instance_method_transactional
