# Paper Analysis Tools

论文分析工具集，用于处理 CER (China Economic Review) 和《经济研究》论文。

## 环境

```bash
# Python 环境
/home/ubuntu/xlerobot-sim/venv/bin/python

# 工作目录
/home/ubuntu/.openclaw/workspace/
```

---

## 脚本说明

### 1. paper_analyzer.py

**单篇论文分析器** - 从 PDF 提取元数据并生成 JSON 分析文件。

```bash
python paper_analyzer.py <pdf_path> --json -o <output.json>
```

**功能**：
- 提取标题、作者、摘要、关键词
- 识别 JEL 代码（原文 + 推断）
- 提取研究方法、行业领域
- 支持中英文论文

**输出示例**：
```json
{
  "title": "Air pollution and entrepreneurship",
  "keywords": ["Air pollution", "Entrepreneurship"],
  "jel_codes": [{"code": "J24", "confidence": 1.0, "source": "paper"}],
  "methods": ["DID", "Panel Data"],
  "industries": ["Environmental Economics"]
}
```

---

### 2. bimonthly_report.py

**双月汇总与热力图生成器** - 按双月生成统计报告和可视化图表。

```bash
python bimonthly_report.py CER05-06/
python bimonthly_report.py 经济研究05-06/
```

**功能**：
- 生成每个双月目录的 `summary.md` 汇总
- 生成 JEL 三级分类图表 (L1/L2/L3)
- 生成行业、方法分布图
- 生成跨双月的组合热力图
- 方法名称自动标准化（合并同类项）

**输出**：
```
期刊目录/
├── heatmap_jel_l1.png      # JEL 一级趋势热力图
├── heatmap_jel_l2.png      # JEL 二级趋势热力图
├── heatmap_jel_l3.png      # JEL 三级趋势热力图
├── heatmap_industry.png    # 行业趋势热力图
├── heatmap_method.png      # 方法趋势热力图
└── 2025-02/
    ├── summary.md          # 双月汇总
    └── charts/
        ├── jel_l1.png
        ├── jel_l2.png
        ├── jel_l3.png
        ├── industry.png
        └── method.png
```

**配置**：
- 截止期限：`2026-02`（组合热力图只包含此前数据）
- JEL 分类：L1=大类(A-Z), L2=中类(A1-Z9), L3=小类(A11-Z99)

---

### 3. journal_comparison.py

**期刊对比分析** - 生成两期刊的对比可视化图表。

```bash
python journal_comparison.py
```

**功能**：
- 雷达图：JEL 大类分布对比
- 双条形图：研究方法偏好对比
- 折线图：主题随时间的趋势对比
- 堆叠面积图：各期刊主题演变
- 差异热力图：JEL 二级分类差异分析

**输出目录**：`/home/ubuntu/.openclaw/workspace/comparison/`

**生成的图表**：
| 文件 | 说明 |
|------|------|
| `radar_jel.png` | JEL 大类雷达图对比 |
| `methods_comparison.png` | 研究方法双条形图 |
| `trend_jel.png` | JEL 时间趋势 (6 类) |
| `trend_methods.png` | 方法时间趋势 (6 种) |
| `stacked_jel_cer.png` | CER JEL 堆叠面积图 |
| `stacked_jel_jjyj.png` | 经济研究 JEL 堆叠面积图 |
| `stacked_methods_cer.png` | CER 方法堆叠面积图 |
| `stacked_methods_jjyj.png` | 经济研究方法堆叠面积图 |
| `difference_jel.png` | JEL 差异分析图 |

---

### 4. tag_network.py

**标签共现网络图生成器** - 基于论文分析 JSON 生成标签之间的网状关联图。

```bash
python tag_network.py CER05-06/
python tag_network.py 经济研究05-06/
```

**原理**：
- 同一篇论文中同时出现的标签建立链接
- 边的权重 = 共现次数
- 节点大小 ∝ 出现频次

**网络类型**：
| 类型 | 节点 | 说明 |
|------|------|------|
| `jel_l1` | JEL 大类 (A-Z) | 研究领域关联 |
| `jel_l2` | JEL 二级 (A1, B2...) | 细分领域关联 |
| `methods` | 研究方法 | 方法组合模式 |
| `jel_method` | JEL + 方法 | 领域与方法的匹配 |
| `jel_industry` | JEL + 行业 | 领域与行业的关联 |

**输出**：
```
期刊目录/networks/
├── 2025-02_jel_l1.png       # 单双月 JEL 大类网络
├── 2025-02_jel_l2.png       # 单双月 JEL 二级网络
├── 2025-02_methods.png      # 单双月方法网络
├── 2025-02_jel_method.png   # 单双月 JEL-方法跨类型
├── 2025-02_jel_industry.png # 单双月 JEL-行业跨类型
├── ...
├── combined_jel_l1.png      # 汇总 JEL 大类网络
├── combined_jel_l2.png      # 汇总 JEL 二级网络
├── combined_methods.png     # 汇总方法网络
├── combined_jel_method.png  # 汇总 JEL-方法网络
└── combined_jel_industry.png # 汇总 JEL-行业网络
```

**可视化参数**：
- 布局算法：Spring Layout (力导向)
- 节点颜色：JEL 类别使用标准配色，方法/行业用统一色
- 边宽度：根据共现强度调整

**依赖**：
```bash
pip install networkx
```

---

### 5. fix_jel_codes.py

**JEL 代码修复** - 从 PDF 原文提取遗漏的 JEL 代码并更新 JSON。

```bash
python fix_jel_codes.py
```

**功能**：
- 扫描所有 PDF 文件
- 使用正则匹配多行格式的 JEL 代码
- 更新对应 JSON 文件，标记 `source: "paper"`

---

### 6. cleanup_duplicates.py

**清理重复 JSON** - 删除重复的分析文件。

```bash
python cleanup_duplicates.py
```

**功能**：
- 基于论文标题 (title 字段) 识别重复
- 保留文件名较长/较新的版本
- 删除简短文件名或 UUID 后缀版本

---

### 7. map_cn_jel.py

**中文关键词→JEL 映射** - 为中文论文补充 JEL 代码。

```bash
python map_cn_jel.py
```

**功能**：
- 基于关键词和标题推断 JEL 代码
- 使用预定义的中文→JEL 映射规则
- 更新 JSON 文件，标记 `source: "inferred"`

---

## 目录结构

```
/home/ubuntu/.openclaw/workspace/
├── CER05-06/                    # China Economic Review
│   ├── 2025-02/
│   │   ├── *.pdf
│   │   ├── analysis/*.json
│   │   ├── summary.md
│   │   └── charts/
│   ├── 2025-04/
│   ├── ...
│   ├── heatmap_*.png
│   └── networks/                # 共现网络图
│       ├── combined_*.png
│       └── 2025-02_*.png
├── 经济研究05-06/                # 经济研究
│   ├── 2025-02/
│   ├── ...
│   ├── heatmap_*.png
│   └── networks/
└── comparison/                  # 对比分析输出
    ├── ANALYSIS_REPORT.md       # 对比分析报告
    ├── NETWORK_ANALYSIS.md      # 网络结构分析报告
    ├── radar_jel.png
    ├── methods_comparison.png
    ├── industry_comparison.png
    ├── trend_*.png
    └── ...
```

---

## JEL 分类参考

| 代码 | 领域 |
|------|------|
| A | General Economics & Teaching |
| B | History of Economic Thought |
| C | Mathematical & Quantitative Methods |
| D | Microeconomics |
| E | Macroeconomics & Monetary |
| F | International Economics |
| G | Financial Economics |
| H | Public Economics |
| I | Health, Education, Welfare |
| J | Labor & Demographics |
| K | Law & Economics |
| L | Industrial Organization |
| M | Business Administration |
| N | Economic History |
| O | Development & Technology |
| P | Economic Systems |
| Q | Agricultural & Environmental |
| R | Urban & Regional |
| Z | Other Special Topics |

---

## 常用命令

```bash
# 分析单篇论文
python paper_analyzer.py paper.pdf --json -o output.json

# 生成双月报告
python bimonthly_report.py CER05-06/

# 对比两期刊
python journal_comparison.py

# 生成共现网络图
python tag_network.py CER05-06/

# 修复 JEL 代码
python fix_jel_codes.py

# 清理重复
python cleanup_duplicates.py
```

---

*Created: 2026-03-15*
