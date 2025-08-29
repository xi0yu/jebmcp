# -*- coding: utf-8 -*-
"""
Signature utilities module - handles JNI signature conversion and validation
"""
import re

def is_valid_jni_signature(class_name):
    """检查是否是有效的 JNI 类型签名"""
    if not class_name:
        return False
    pattern = r'^L[^;]+;$'
    return re.match(pattern, class_name) is not None

def convert_class_signature(class_name):
    """
    将类名转换为 JNI 风格的签名格式
    如果不是以 'L' 开头、';' 结尾，则进行转换
    
    Args:
        class_name: 类名字符串，可以是普通格式或JNI签名格式
        
    Returns:
        符合JNI签名格式的字符串
    """
    if not class_name:
        return None
    if is_valid_jni_signature(class_name):
        return class_name
    else:
        return 'L' + class_name.replace('.', '/') + ';'

def normalize_method_signature(method_signature):
    """
    标准化方法签名，确保格式正确
    
    Args:
        method_signature: 方法签名字符串
        
    Returns:
        标准化后的方法签名
    """
    if not method_signature:
        return None
    
    # 如果已经是完整的方法签名，直接返回
    if '->' in method_signature and '(' in method_signature and ')' in method_signature:
        return method_signature
    
    # 否则尝试构造完整签名（这里可能需要更多上下文信息）
    return method_signature
