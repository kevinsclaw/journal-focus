#!/usr/bin/env python3
"""
清理重复的JSON文件

对于同一篇论文的多个JSON版本，保留文件名最长的（最完整的）
"""

import os
import re
from collections import defaultdict

BASE_DIR = "/home/ubuntu/.openclaw/workspace/经济研究05-06"

def get_title_key(filename):
    """提取论文标题的前8个字符作为key"""
    # 去掉期号前缀
    match = re.match(r'^(\d{2}-\d{1,2})-(.+)\.json$', filename)
    if match:
        prefix = match.group(1)
        title = match.group(2)
        # 去掉UUID后缀
        title = re.sub(r'---[a-f0-9]{8}-.*$', '', title)
        # 取前8个字符
        key = title[:8]
        return prefix, key
    return None, None

def main():
    total_deleted = 0
    
    for folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        
        analysis_dir = os.path.join(folder_path, "analysis")
        if not os.path.exists(analysis_dir):
            continue
        
        print(f"\n📁 {folder}")
        
        # 按(期号, 标题key)分组
        groups = defaultdict(list)
        for f in os.listdir(analysis_dir):
            if not f.endswith('.json'):
                continue
            prefix, key = get_title_key(f)
            if prefix and key:
                groups[(prefix, key)].append(f)
        
        # 检查每个组
        folder_deleted = 0
        for (prefix, key), files in groups.items():
            if len(files) > 1:
                # 保留最长的文件名
                files_sorted = sorted(files, key=len, reverse=True)
                keep = files_sorted[0]
                delete = files_sorted[1:]
                
                for f in delete:
                    path = os.path.join(analysis_dir, f)
                    print(f"  删除: {f}")
                    os.remove(path)
                    folder_deleted += 1
        
        if folder_deleted == 0:
            print("  无重复")
        else:
            print(f"  删除: {folder_deleted} 个")
            total_deleted += folder_deleted
    
    print(f"\n{'='*50}")
    print(f"总计删除: {total_deleted} 个重复文件")
    
    # 统计最终数量
    total_json = sum(
        len([f for f in os.listdir(os.path.join(BASE_DIR, d, "analysis")) if f.endswith('.json')])
        for d in os.listdir(BASE_DIR)
        if os.path.isdir(os.path.join(BASE_DIR, d, "analysis"))
    )
    print(f"剩余JSON: {total_json}")

if __name__ == '__main__':
    main()
