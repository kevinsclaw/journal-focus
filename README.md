# Journal Focus

学术期刊论文分析与可视化项目，对比分析 **China Economic Review** 与**《经济研究》**两本顶级经济学期刊的研究趋势。

## 📊 项目概览

| 期刊 | 时间范围 | 论文数量 | JEL代码 |
|------|----------|----------|---------|
| China Economic Review (CER) | 2025-02 ~ 2026-02 | 262篇 | 278种 |
| 经济研究 (JJYJ) | 2025-02 ~ 2026-02 | 152篇 | 154种 |
| **合计** | - | **414篇** | - |

## 📁 目录结构

```
journal-focus/
├── README.md
├── tools/                          # 分析工具脚本
│   ├── paper_analyzer.py           # 主分析脚本 (中英文)
│   ├── bimonthly_report.py         # 双月报告 + 热力图
│   ├── journal_comparison.py       # 期刊对比图表
│   ├── tag_network.py              # 共现网络可视化
│   ├── fix_jel_codes.py            # JEL代码修复
│   ├── map_cn_jel.py               # 中文→JEL映射
│   └── ...
└── analysis_result/                # 分析结果
    ├── CER05-06/                   # China Economic Review
    │   ├── 2025-02/ ~ 2026-02/     # 按双月分组
    │   │   ├── analysis/*.json     # 论文分析JSON
    │   │   ├── charts/*.png        # 统计图表
    │   │   └── summary.md          # 期号汇总
    │   ├── heatmap_*.png           # 时序热力图
    │   └── networks/               # 网络图
    ├── 经济研究05-06/               # 经济研究
    │   └── (同上结构)
    └── comparison/                 # 跨期刊对比
        ├── ANALYSIS_REPORT.md      # 综合分析报告
        ├── NETWORK_ANALYSIS.md     # 网络分析报告
        └── *.png                   # 对比图表
```

## 🔬 分析维度

### 1. JEL 分类
三级 JEL 代码分析：
- **L1** (一级): 19个大类 (A-Z)
- **L2** (二级): 如 F1, G2, O3
- **L3** (三级): 完整代码如 F14, G21, O33

### 2. 研究方法
识别并标准化的方法论：
- **实证**: DID, IV, Panel, FE, RDD, PSM, GMM
- **理论**: GE (一般均衡), Game Theory, Structural Model
- **其他**: ML/NLP, Experiment, Survey

### 3. 行业领域
- Digital Economy, Finance, Labor, Trade, Environment
- Manufacturing, Real Estate, Agriculture, Energy...

## 📈 可视化输出

### 热力图 (Heatmaps)
按时间序列展示各维度的研究热度变化：
- `heatmap_jel_l1.png` - JEL一级分类趋势
- `heatmap_jel_l2.png` - JEL二级分类趋势
- `heatmap_industry.png` - 行业分布趋势
- `heatmap_method.png` - 方法论趋势

### 网络图 (Networks)
展示标签间的共现关系：
- `jel_l1.png` - JEL大类共现网络
- `jel_method.png` - JEL-方法关联网络
- `jel_industry.png` - JEL-行业关联网络

### 对比图表
- `trend_*.png` - 时序趋势对比
- `radar_jel.png` - JEL分布雷达图
- `stacked_*.png` - 堆叠面积图

## 🛠 工具使用

### 安装依赖
```bash
pip install pymupdf openai matplotlib networkx pandas numpy
```

### 分析单篇论文
```bash
python tools/paper_analyzer.py paper.pdf --json -o output.json
```

### 生成双月报告
```bash
python tools/bimonthly_report.py /path/to/journal/
```

### 生成对比分析
```bash
python tools/journal_comparison.py /path/to/cer/ /path/to/jjyj/ -o comparison/
```

### 生成网络图
```bash
python tools/tag_network.py /path/to/journal/ --type jel_l1
```

## 📋 JSON 输出格式

每篇论文生成一个 JSON 文件：

```json
{
  "title": "Digital financial inclusion and income inequality",
  "authors": ["Zhang San", "Li Si"],
  "keywords": ["Digital finance", "Income inequality", "DID"],
  "abstract": "This paper examines...",
  "jel_codes": [
    {"code": "G21", "confidence": 1.0, "source": "paper"},
    {"code": "O33", "confidence": 0.8, "source": "inferred"}
  ],
  "methods": ["DID", "Panel Data", "IV"],
  "industries": ["Digital Economy", "Finance"],
  "issue": "25-02",
  "source_file": "25-02-Digital financial inclusion.pdf"
}
```

## 📊 主要发现

详见 `analysis_result/comparison/ANALYSIS_REPORT.md`

**CER vs 经济研究 对比**:
- CER 更侧重微观实证 (DID/IV 主导)
- 经济研究 更多理论建模 (一般均衡/博弈论)
- 共同热点: 数字经济、绿色发展、区域协调

## 📄 License

MIT

## 🔗 Related

- [China Economic Review](https://www.sciencedirect.com/journal/china-economic-review)
- [经济研究](http://www.erj.cn/)
- [JEL Classification](https://www.aeaweb.org/econlit/jelCodes.php)
