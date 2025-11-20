# -*- coding: utf-8 -*-

from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.units.code.android.dex import IDexCodeItem
from java.lang import System
import sys
import os

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录（src的上级目录）
project_root = os.path.dirname(os.path.dirname(current_dir))
jar_path = os.path.join(project_root, "assets", "PBDecoder.jar")

# 检查assets目录是否存在 PBDecoder.jar
if os.path.exists(jar_path):
  sys.path.append(jar_path)
else:
  sys.path.append(r"D:\tools\PBDecoder.jar")

System.setProperty("python.security.respectJavaAccessibility", "false")
from com.wwb.proto import PBMain

class ProtoParser(object):
    """独立的protobuf解析器，用于MCP集成"""
    
    def __init__(self, dex_unit):
        self.dex_unit = dex_unit
        self.parsed_class = []
    
    def parse_class(self, class_signature):
        """解析指定类的protobuf定义"""
        if not class_signature:
            return None
        
        try:
            # 确保类签名格式正确
            if not class_signature.startswith('L'):
                class_signature = 'L' + class_signature
            if not class_signature.endswith(';'):
                class_signature = class_signature + ';'
            
            clazz = self.dex_unit.getClass(class_signature)
            if clazz is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}
            
            # 重置已解析类列表
            self.parsed_class = []
            
            proto_result = self._parse_cls(clazz)
            return {
                "success": True,
                "class_signature": class_signature,
                "proto_definition": proto_result,
                "message": "Protobuf definition parsed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": "Failed to parse protobuf: %s" % str(e)}
    
    def _parse_cls(self, cls):
        """内部方法：解析类"""
        self.parsed_class.append(cls.getName())
        current_proto = self._parse_proto(cls)
        
        cresultstr = "message " + cls.getName() + " {\n"
        subresult = ""
        for fields in current_proto.split("\n"):
            if not len(fields) > 0: 
                continue
            if "{" in fields or "}" in fields:
                cresultstr += "\t" + fields + "\n"
                continue
            field = fields.split("=")[0].split(" ")
            mfieldType = field[1] if not "oneof" in field[1] else field[0]
            mfieldType = mfieldType.strip()
            if mfieldType == "message" or mfieldType == "group":
                for clsField in cls.getFields():
                    if clsField.getName(True) == field[2] or clsField.getName(False) == field[2]:
                        mtype = clsField.getFieldType()
                        cresultstr += "\t" + fields.replace(mfieldType, mtype.getName()) + "\n"
                        if mtype.getName() in self.parsed_class: 
                            continue
                        subresult += self._parse_cls(mtype.getImplementingClass())
                continue
            
            if mfieldType == "enum":
                fields = fields.replace("enum", "int32") + " //unknow enum"
            if "/" in mfieldType:
                fields = fields.replace(mfieldType, mfieldType.split("/")[1])
            cresultstr += "\t" + fields + "\n"
            
            if not self._is_base_type(mfieldType):
                if "/" in mfieldType:
                    if mfieldType.split("/")[1] in self.parsed_class: 
                        continue
                if mfieldType in self.parsed_class: 
                    continue
                subresult += self._parse_cls(self.dex_unit.getClass("L" + mfieldType + ";"))
        
        return cresultstr + "}\n\n" + subresult
    
    def _is_base_type(self, mtype):
        """检查是否为基本类型"""
        for basetype in ["enum", "string", "int", "double", "float", "bool", "fixed", "bytes", "oneof", "map", "group"]:
            if basetype in mtype:
                return True
        return False
    
    def _parse_proto(self, cls):
        """解析protobuf定义"""
        if cls is None:
            raise Exception("Class is None")

        methods = cls.getMethods()
        if methods is None:
            raise Exception("No methods found in class")

        for method in methods:
            if method is None:
                continue
            if method.getName() == "<init>" or method.getName() == "<clinit>":
                continue

            method_data = method.getData()
            if method_data is None:
                continue
            codeItem = method_data.getCodeItem()

            objs = {}
            messageinfo = ""
            objkeys = []
            aputobjs = {}
            constRegs = {}
            constRegsComplete = False
            if isinstance(codeItem, IDexCodeItem):
                instructions = codeItem.getInstructions()
                if instructions is None:
                    continue
                for firststr, ins in enumerate(instructions):
                    if ins is None:
                        continue
                    if ins.getMnemonic() == "const/4":
                        if not constRegsComplete:
                            operand0 = ins.getOperand(0)
                            operand1 = ins.getOperand(1)
                            if operand0 is not None and operand1 is not None:
                                constRegs[operand0.getValue()] = operand1.getValue()
                        continue
                    if "if-eq" == ins.getMnemonic():
                        operand1 = ins.getOperand(1)
                        if operand1 is not None:
                            try:
                                if constRegs.get(ins.getOperand(0).getValue(), 0) == 2:
                                    constRegsComplete = True
                                    continue
                            except:
                                continue
                    if ins.getMnemonic() == "const-string":
                        break

                if firststr == len(instructions) - 1:
                    continue  # incorrect method!
                objcomplete = False
                while True:
                    if firststr >= len(instructions):
                        break
                    ins = instructions[firststr]
                    firststr += 1
                    if ins is None:
                        continue
                    if ins.getMnemonic() == "const-string":
                        string_index = ins.getOperand(1)
                        if string_index is not None:
                            string_obj = self.dex_unit.getString(string_index.getValue())
                            if string_obj is not None:
                                conststr = string_obj.getValue()
                                if conststr is not None:
                                    if "\x01" in conststr or "\x02" in conststr or "\x03" in conststr or "\x00" in conststr:
                                        messageinfo = conststr
                                    else:
                                        if not objcomplete:
                                            operand0 = ins.getOperand(0)
                                            if operand0 is not None:
                                                objs[operand0.getValue()] = conststr
                        continue
                    if ins.getMnemonic() == "const-class":
                        if not objcomplete:
                            type_index = ins.getOperand(1)
                            if type_index is not None:
                                type_obj = self.dex_unit.getType(type_index.getValue())
                                if type_obj is not None and type_obj.getAddress() is not None:
                                    address = type_obj.getAddress()
                                    if len(address) > 2:  # Ensure valid address format
                                        objs[ins.getOperand(0).getValue()] = address[1:-1]
                        continue
                    if "const/" in ins.getMnemonic():
                        operand0 = ins.getOperand(0)
                        operand1 = ins.getOperand(1)
                        if operand0 is not None and operand1 is not None:
                            objs[operand0.getValue()] = operand1.getValue()
                        continue
                    if ins.getMnemonic() == "sget-object":
                        if not objcomplete:
                            operand0 = ins.getOperand(0)
                            if operand0 is not None:
                                objs[operand0.getValue()] = "enum.type"
                        continue
                    if "move-object" in ins.getMnemonic():
                        if not objcomplete:
                            operand0 = ins.getOperand(0)
                            operand1 = ins.getOperand(1)
                            if operand0 is not None and operand1 is not None:
                                src_val = operand1.getValue()
                                if src_val in objs:
                                    objs[operand0.getValue()] = objs[src_val]
                        continue
                    if "filled-new-array" in ins.getMnemonic():
                        if "range" in ins.getMnemonic():
                            objkeys = sorted(objs.keys())
                        else:
                            operands = ins.getOperands()
                            if operands:
                                objkeys = [item.getValue() for item in operands[1:] if item is not None]
                        objcomplete = True
                        continue
                    if "aput-object" == ins.getMnemonic():
                        operand0 = ins.getOperand(0)
                        operand2 = ins.getOperand(2)
                        if operand0 is not None and operand2 is not None:
                            key = operand2.getValue()
                            if key in objs:
                                key = objs[key]
                            elif key in constRegs:
                                key = constRegs[key]
                            else:
                                continue
                            src_val = operand0.getValue()
                            if src_val in objs:
                                aputobjs[key] = objs[src_val]
                        continue
                    if "move-result" in ins.getMnemonic():
                        operand0 = ins.getOperand(0)
                        if operand0 is not None:
                            objs[operand0.getValue()] = "enum.type"
                        continue
                    if firststr >= len(instructions) - 1:
                        break
                if len(messageinfo) < 2:
                    continue
                else:
                    break

        if len(messageinfo) < 2:
            raise Exception("Unexpected messageinfo!")
        if len(objs) < 1:
            return ""
        if aputobjs:
            objs = aputobjs
            objkeys = sorted(aputobjs.keys())
        return PBMain.forJeb(self._to_unicode_escape(messageinfo), ''.join(objs[key] + "," for key in objkeys if key in objs))
    
    def _to_unicode_escape(self, s):
        """转换为Unicode转义序列"""
        return ''.join('\\u%04X' % ord(c) if ord(c) <= 0xFFFF else '\\u%08X' % ord(c) for c in s)


# 保持原有的JEB脚本接口以向后兼容
class protoParser(object):
    """JEB脚本接口，保持向后兼容"""
    
    def run(self, ctx):
        from com.pnfsoftware.jeb.client.api import FormEntry
        prj = ctx.getMainProject()
        dexUnit = prj.findUnit(IDexUnit)
        
        className = ctx.displayForm("proto class", "the class of protobuf",
                                   FormEntry.Text('className', '', FormEntry.INLINE, None, 0, 0))[0]
        
        parser = ProtoParser(dexUnit)
        result = parser.parse_class(className)
        
        if result["success"]:
            ctx.displayText("proto", result["proto_definition"], True)
        else:
            ctx.displayText("proto", "Error: " + result["error"], True)
