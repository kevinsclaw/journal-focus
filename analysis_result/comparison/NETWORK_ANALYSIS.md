# 标签共现网络分析报告

**China Economic Review (CER) vs 《经济研究》(JJYJ)**

生成时间：2026-03-15

---

## 1. 网络概览

| 网络类型 | CER | 经济研究 |
|----------|-----|----------|
| JEL L1 网络 | 17节点, 88边 | 16节点, 87边 |
| JEL L2 网络 | 34节点, 234边 | 40节点, 294边 |
| Methods 网络 | 13节点, 27边 | 11节点, 26边 |
| JEL-Method 网络 | 27节点, 183边 | 27节点, 178边 |
| JEL-Industry 网络 | 45节点, 351边 | 45节点, 366边 |

**观察**：两刊的网络规模相近，但经济研究的 JEL L2 网络更密集（294边 vs 234边），说明其研究领域更加交叉融合。

---

## 2. JEL 大类共现网络分析

### 2.1 CER 网络结构

**核心节点（高度中心性）**：
- **O (发展/技术)** - 最大节点，与几乎所有类别连接
- **F (国际经济)** - 第二大节点，国际研究是 CER 特色
- **J (劳动经济)** - 第三大节点，劳动市场研究密集
- **I (健康/教育)** - 重要节点，社会政策研究

**边缘节点**：
- Z (其他)、N (经济史)、P (经济体制) - 较为孤立

**强连接对**：
- F ↔ O (国际与发展)
- J ↔ I (劳动与社会)
- D ↔ G (微观与金融)

### 2.2 经济研究网络结构

**核心节点（高度中心性）**：
- **L (产业组织)** - 最大节点，产业研究是经济研究特色
- **D (微观经济)** - 第二大节点，微观分析核心
- **O (发展/技术)** - 第三大节点
- **G (金融)** - 重要节点，金融研究密集

**边缘节点**：
- K (法律经济)、M (企业管理) - 出现较少

**强连接对**：
- L ↔ D (产业与微观)
- L ↔ O (产业与技术)
- G ↔ E (金融与宏观)
- P ↔ B (体制与思想史) - 经济研究特有的连接

### 2.3 结构差异

| 维度 | CER | 经济研究 |
|------|-----|----------|
| 网络中心 | O-F-J 三角 | L-D-O 三角 |
| 最密集区域 | 国际-劳动-发展 | 产业-微观-金融 |
| 独特连接 | F↔J (国际劳动) | P↔B (体制思想) |
| 边缘类别 | P, N | K, M |

---

## 3. 研究方法共现网络分析

### 3.1 CER 方法网络

**核心方法**：
- **DID** - 最高频方法，与多数方法共现
- **Panel** - 第二核心，面板数据分析普遍
- **IV** - 工具变量法常用
- **Exp (实验)** - CER 特色方法

**方法组合模式**：
- DID + Panel + IV (经典因果识别组合)
- Exp + Game (实验经济学)
- PSM + DID (匹配+双差分)

**孤立方法**：
- Structural (结构估计) - 较少与其他方法组合

### 3.2 经济研究方法网络

**核心方法**：
- **DID** - 同样是最高频
- **FE (固定效应)** - 核心方法
- **GE (一般均衡)** - 经济研究特色
- **Game (博弈论)** - 理论建模特色

**方法组合模式**：
- DID + FE + IV (实证组合)
- GE + Game (理论组合)
- NLP + DID (文本+因果)

**独特组合**：
- IO (投入产出) + Spatial (空间分析)
- GE + Quasi-Exp (理论+准实验)

### 3.3 方法网络差异

| 维度 | CER | 经济研究 |
|------|-----|----------|
| 方法中心 | DID-Panel-IV | DID-FE-GE |
| 特色方法 | Experiment | GE, Game, IO |
| 方法多样性 | 13种 | 11种 |
| 理论-实证平衡 | 偏实证 | 理论实证并重 |

---

## 4. JEL-Method 跨类型网络分析

### 4.1 CER 跨类型关联

**强关联对**：
| JEL | 偏好方法 |
|-----|----------|
| J (劳动) | DID, Panel, Exp |
| I (健康/教育) | Exp, DID |
| F (国际) | Panel, IV |
| Q (环境) | DID, IV |
| D (微观) | Exp, Game |

**观察**：
- **实验方法 (Exp)** 集中在 I、J、D 类别
- **面板数据 (Panel)** 在 F、J 类别最常见
- 方法选择与研究领域高度相关

### 4.2 经济研究跨类型关联

**强关联对**：
| JEL | 偏好方法 |
|-----|----------|
| L (产业) | DID, FE, GE |
| D (微观) | Game, FE |
| O (发展) | DID, IV, GE |
| G (金融) | FE, DID |
| E (宏观) | GE, Quasi-Exp |

**观察**：
- **一般均衡 (GE)** 集中在 L、O、E 类别
- **博弈论 (Game)** 主要用于 D、L 类别
- **NLP/文本分析** 跨多个类别使用

### 4.3 方法-领域匹配差异

| 方法 | CER 偏好领域 | 经济研究偏好领域 |
|------|-------------|------------------|
| DID | J, Q, I | L, O, G |
| Panel | F, J | - (较少) |
| Exp | I, J, D | - (几乎没有) |
| GE | - (较少) | L, E, O |
| Game | D | D, L |

---

## 5. JEL-Industry 跨类型网络分析

### 5.1 CER 行业-领域关联

**核心行业节点**：
- Manufacturing（制造业）
- Healthcare（医疗）
- Education（教育）
- Agriculture（农业）
- Banking/Financial Services（银行/金融服务）

**强关联**：
| JEL | 关联行业 |
|-----|----------|
| I | Healthcare, Education, Social Services |
| J | Labor market, Manufacturing |
| F | International Trade, Manufacturing |
| G | Banking, Financial Services, Finance |
| Q | Agriculture, Environmental Services, Energy |

**特色**：
- Healthcare-Education 形成社会服务集群
- International Trade 与 F 类别强绑定

### 5.2 经济研究行业-领域关联

**核心行业节点**：
- Manufacturing（制造业）
- Finance（金融）
- Digital Economy（数字经济）
- Services（服务业）
- Public（公共部门）

**强关联**：
| JEL | 关联行业 |
|-----|----------|
| L | Manufacturing, Services, Digital Economy |
| G | Finance, Banking |
| O | Technology, AI, Platform, Digital Economy |
| F | Trade, Cross-border, Supply Chain |
| H | Public, Government |
| P | Public, Government |

**特色**：
- **数字经济集群**：AI, Platform, Internet, Digital Economy, IT 形成密集子网络
- **供应链集群**：Supply Chain, Cross-border, Trade 与 F、L 强关联

### 5.3 行业焦点差异

| CER 独有/偏好 | 经济研究独有/偏好 |
|--------------|-------------------|
| Healthcare | Digital Economy |
| Higher Education | AI/Platform |
| Labor market | Supply Chain |
| Industrial robotics | Public/Government |
| Social Services | Cross-border |

---

## 6. 网络结构核心发现

### 6.1 研究范式差异

**CER**：
- **国际-劳动-社会** 三角核心
- 实证驱动，实验方法突出
- 行业焦点：医疗、教育、劳动市场

**经济研究**：
- **产业-微观-金融** 三角核心
- 理论实证并重，均衡模型常见
- 行业焦点：制造业、数字经济、公共部门

### 6.2 交叉融合程度

经济研究的网络更密集（更多边），说明：
- 研究更加**交叉学科**
- 单篇论文涉及更多 JEL 类别
- 方法组合更多样

### 6.3 新兴主题

从网络中可识别的**新兴研究主题**：

| 主题 | CER 表现 | 经济研究表现 |
|------|---------|-------------|
| 数字经济 | 中等 | **强** |
| AI/机器人 | 中等 | **强** |
| 供应链 | 中等 | **强** |
| 碳排放/绿色 | 强 | 强 |
| 平台经济 | 弱 | **强** |

### 6.4 方法论趋势

- **DID** 是两刊共同的主流方法
- **文本分析/NLP** 在经济研究更常见
- **实验方法** 是 CER 的方法论特色
- **一般均衡建模** 是经济研究的理论特色

---

## 7. 可视化图表索引

所有网络图保存位置：

**CER05-06/networks/**
```
combined_jel_l1.png      # JEL 大类网络
combined_jel_l2.png      # JEL 二级网络
combined_methods.png     # 方法网络
combined_jel_method.png  # JEL-方法跨类型
combined_jel_industry.png # JEL-行业跨类型
```

**经济研究05-06/networks/**
```
combined_jel_l1.png
combined_jel_l2.png
combined_methods.png
combined_jel_method.png
combined_jel_industry.png
```

**每个双月目录** 也有对应的网络图（如 `2025-02_jel_l1.png`）。

---

## 附录：网络分析方法说明

### 共现定义
- 同一篇论文中同时出现的标签建立链接
- 边的权重 = 共现次数

### 可视化参数
- 节点大小 ∝ 出现频次
- 边宽度 ∝ 共现强度
- 布局算法：Spring Layout (力导向)
- 颜色：JEL 类别使用标准配色

### 过滤阈值
- 汇总网络：min_node_count=3-5, min_edge_weight=2-3
- 双月网络：min_node_count=2, min_edge_weight=1

---

*报告生成工具: `tag_network.py`*
*分析基于 2025-02 至 2026-02 数据*
