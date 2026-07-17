import xml.etree.ElementTree as ET

# 读取生成的 en.ts
tree = ET.parse('en.ts')
root = tree.getroot()

count = 0
for message in root.iter('message'):
    source = message.find('source')
    translation = message.find('translation')
    
    if source is not None and translation is not None:
        # 如果 translation 是 unfinished 或为空
        if translation.get('type') == 'unfinished' or translation.text is None:
            translation.text = source.text
            # 移除 unfinished 标记
            translation.attrib.pop('type', None)
            count += 1

# 保存
tree.write('en.ts', encoding='utf-8', xml_declaration=True)
print(f'已处理 {count} 个翻译条目')
