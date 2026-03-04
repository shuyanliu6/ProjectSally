# 📐 Project Sally - 架构概览

## 系统整体设计

你的量化交易系统分为 **5 个核心层**，从下到上依次是：

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: 应用层 (Scripts & Orchestration)                  │
│  ├─ ingest_data.py      (数据摄入脚本)                       │
│  ├─ generate_quality_report.py  (质量报告)                   │
│  └─ test_setup.py       (测试脚本)                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: 业务逻辑层 (ETL & Validation)                      │
│  ├─ pipelines.py        (数据管道)                           │
│  ├─ data_providers.py   (数据源适配)                         │
│  ├─ sanity_checks.py    (数据异常检测)                       │
│  └─ pit_logic.py        (防止前瞻偏差)                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 数据访问层 (Database)                              │
│  ├─ connection.py       (数据库连接)                         │
│  └─ schema.py           (表结构定义)                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 配置层 (Configuration)                             │
│  └─ config.py           (全局配置)                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 基础设施 (Infrastructure)                          │
│  ├─ Docker              (容器化)                             │
│  ├─ PostgreSQL + TimescaleDB  (数据库)                       │
│  └─ Python 3.11         (运行时)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 数据流向

### 完整的数据流程：

```
┌──────────────────┐
│  Polygon.io      │  ← 外部数据源
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│  data_providers.py               │  ← 数据源适配层
│  (PolygonProvider)               │
│  - 获取股票价格                   │
│  - 获取分红信息                   │
│  - 获取拆股信息                   │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  pipelines.py                    │  ← ETL 管道
│  (DataPipeline)                  │
│  - 资产管理 (Asset Management)   │
│  - 价格摄入 (Price Ingestion)    │
│  - 分红处理 (Dividend Handling)  │
│  - 拆股处理 (Split Handling)     │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  validation/                     │  ← 数据验证层
│  - sanity_checks.py              │
│  - pit_logic.py                  │
│  (检测异常、防止前瞻偏差)         │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  connection.py                   │  ← 数据库访问
│  (SQLAlchemy ORM)                │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  PostgreSQL + TimescaleDB        │  ← 持久化存储
│  6 个表:                          │
│  - assets                        │
│  - daily_prices (hypertable)     │
│  - dividends                     │
│  - splits                        │
│  - fundamentals                  │
│  - metadata                      │
└──────────────────────────────────┘
```

---

## 核心概念解释

### 1. **为什么分层？**

**分层的好处：**
- **单一职责** - 每层只做一件事
- **易于测试** - 可以独立测试每一层
- **易于维护** - 改动一层不影响其他层
- **易于扩展** - 添加新功能只需添加新层或修改特定层
- **代码复用** - 不同的脚本可以共用同一层

**例如：** 如果你想从 Yahoo Finance 切换到 Polygon.io，只需修改 `data_providers.py`，其他层完全不用改。

### 2. **为什么用 PostgreSQL + TimescaleDB？**

**PostgreSQL：**
- 开源、免费、稳定
- 支持复杂的 SQL 查询
- 支持 JSON 数据类型（用于存储元数据）

**TimescaleDB：**
- 时间序列数据库扩展
- 自动压缩历史数据（节省空间）
- 查询速度快 10-100 倍
- 完美适合股票价格数据（时间序列）

### 3. **为什么需要验证层？**

**两个主要问题：**

**问题 1：数据异常**
- 股票价格突然下跌 90%（通常是数据错误，不是真实事件）
- 成交量为 0（数据缺失）
- OHLC 数据不合理（High < Low）

**问题 2：前瞻偏差 (Look-Ahead Bias)**
- 在回测时，不能使用"未来"的数据
- 例如：今天的收盘价只能在明天才知道
- 如果在今天使用明天的数据进行决策，就是前瞻偏差
- 这会导致回测结果虚假，实际交易时表现很差

**验证层的作用：**
- SanityChecker：检测数据异常
- PITValidator：确保时间顺序正确（防止前瞻偏差）

---

## 关键设计决策

### 1. **为什么用 Docker？**

**问题：** 在你的 Mac 开发，在 Windows PC 交易，可能环境不一样
**解决方案：** Docker 确保所有地方环境完全相同
**好处：**
- 开发环境 = 测试环境 = 生产环境
- 不会出现"在我的电脑上能跑"的问题
- 易于部署到云服务器

### 2. **为什么用 ORM (SQLAlchemy)？**

**ORM = Object-Relational Mapping**

**问题：** 直接写 SQL 容易出错，代码不易维护
**解决方案：** 用 Python 对象代表数据库表

```python
# 不用 ORM（直接 SQL）
cursor.execute("INSERT INTO assets (symbol, name) VALUES (%s, %s)", ("AAPL", "Apple"))

# 用 ORM（Python 对象）
asset = Asset(symbol="AAPL", name="Apple")
session.add(asset)
session.commit()
```

**好处：**
- 代码更清晰
- 自动处理数据类型转换
- 防止 SQL 注入
- 易于测试

### 3. **为什么分离"资产"和"价格"？**

**表结构：**
```
assets 表：
- id (主键)
- symbol (股票代码，如 AAPL)
- name (公司名称)
- exchange (交易所)
- ...

daily_prices 表：
- id (主键)
- asset_id (外键，指向 assets)
- date (日期)
- open, high, low, close (OHLC)
- volume (成交量)
- ...
```

**为什么分离？**
- **避免重复** - AAPL 的信息只存一次
- **查询效率** - 查询特定股票的价格时，只需查一个表
- **数据一致性** - 修改 AAPL 的名称，只需改一个地方
- **灵活性** - 可以轻松添加新的资产类型（基金、债券等）

---

## 配置管理

**config.py 的作用：**
- 集中管理所有配置
- 从环境变量读取敏感信息（密码、API 密钥）
- 提供默认值
- 不同环境使用不同配置（开发、测试、生产）

**环境变量示例：**
```bash
DB_HOST=database
DB_USER=stock_user
DB_PASSWORD=secure_password_123
DATA_PROVIDER=polygon  # 或 yfinance
POLYGON_API_KEY=your_api_key_here
```

---

## 数据流详细步骤

### 当你运行 `ingest_data.py --ticker AAPL` 时：

1. **配置加载** (`config.py`)
   - 读取环境变量
   - 设置数据库连接参数
   - 设置数据提供者

2. **数据获取** (`data_providers.py`)
   - 创建 PolygonProvider 实例
   - 调用 Polygon.io API
   - 获取 AAPL 的历史价格、分红、拆股

3. **数据管道** (`pipelines.py`)
   - 创建或更新 AAPL 资产记录
   - 批量插入价格数据
   - 处理分红和拆股

4. **数据验证** (`validation/`)
   - SanityChecker 检测异常
   - PITValidator 检查时间顺序
   - 生成验证报告

5. **数据库存储** (`connection.py` + `schema.py`)
   - 通过 SQLAlchemy ORM 插入数据
   - 数据持久化到 PostgreSQL

6. **完成**
   - 生成摄入报告
   - 显示摄入统计

---

## 现在的问题和改进空间

### 当前的问题：
1. ❌ 数据源是 yfinance，限流严重
2. ❌ 没有错误恢复机制（如果中途失败，需要重新开始）
3. ❌ 没有增量更新（每次都是全量更新）
4. ❌ 没有数据缓存
5. ❌ 没有并发处理（一次只能处理一个股票）

### 改进计划：
1. ✅ 集成 Polygon.io（你已经决定了）
2. 🔄 添加断点续传（如果失败，从上次位置继续）
3. 🔄 添加增量更新（只更新新数据）
4. 🔄 添加缓存层（避免重复查询）
5. 🔄 添加并发处理（同时处理多个股票）

---

## 总结

**你的系统是一个标准的 ETL 架构：**

```
Extract (提取) → Transform (转换) → Load (加载)
  ↓                ↓                  ↓
Polygon.io    验证 + 清洗          数据库
```

**每一层都有明确的职责，易于测试和维护。**

---

## 接下来

现在你理解了整个架构。我们可以：

1. **深入讲解每一层的代码**
2. **集成 Polygon.io**
3. **根据你的建议改进代码**

你想先看哪个文件的详细代码？我建议从 `config.py` 开始，然后是 `data_providers.py`，最后是 `pipelines.py`。

或者你有其他想法？
