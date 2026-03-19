# Massive API 集成文档

## 概述

本文档说明 Project Sally 中 Massive API 数据提供者的集成情况。

## 集成状态

✅ **已完成**

- Massive API 提供者类 (`MassiveDataProvider`) 已实现
- 支持日线数据、分红数据和拆股数据
- 工厂函数 (`get_provider()`) 已更新以支持 "massive" 提供者
- 命令行工具已更新以支持 Massive 作为数据源
- 配置管理已更新以支持 API 密钥

## 功能实现

### 1. 日线数据 (Daily Prices)

**端点：** `GET /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}`

**功能：** 获取指定日期范围内的 OHLCV 数据

**状态：** ✅ 工作正常

**示例：**
```python
from src.etl.data_providers import get_provider
from datetime import date

provider = get_provider("massive", api_key="YOUR_API_KEY")
prices = provider.get_daily_prices("AAPL", date(2026, 2, 17), date(2026, 3, 19))
print(prices)
```

**限制：**
- 你的 API 计划似乎只支持**最近的数据**（大约最后 30-60 天）
- 历史数据（2015-2023）需要付费计划升级

### 2. 分红数据 (Dividends)

**端点：** `GET /v3/reference/dividends`

**功能：** 获取股票的分红历史

**状态：** ✅ 工作正常

**示例：**
```python
dividends = provider.get_dividends("AAPL", date(2020, 1, 1), date(2026, 3, 19))
print(dividends)
```

**返回字段：**
- `ex_date` - 除权日期
- `dividend_amount` - 分红金额
- `dividend_type` - 分红类型 (CD, etc.)
- `data_source` - 数据源

### 3. 拆股数据 (Splits)

**端点：** `GET /v3/reference/splits`

**功能：** 获取股票的拆股历史

**状态：** ⚠️ 部分工作（需要参数调整）

## 使用方法

### 初始化提供者

```python
from src.config import get_config
from src.etl.data_providers import get_provider

config = get_config()
provider = get_provider(
    "massive",
    api_key=config.massive_api_key,
)
```

### 验证 Ticker

```python
if provider.validate_ticker("AAPL"):
    print("Ticker is valid")
else:
    print("Ticker is invalid or not found")
```

### 获取数据

```python
from datetime import date, timedelta

today = date.today()
start_date = today - timedelta(days=30)

# 获取日线数据
prices = provider.get_daily_prices("AAPL", start_date, today)

# 获取分红数据
dividends = provider.get_dividends("AAPL", date(2020, 1, 1), today)

# 获取拆股数据
splits = provider.get_splits("AAPL", date(2020, 1, 1), today)
```

## 命令行使用

### 使用 Massive 作为数据源

```bash
python scripts/ingest_data.py \
    --provider massive \
    --ticker AAPL \
    --start-date 2026-02-17 \
    --end-date 2026-03-19 \
    --db-url postgresql://user:pass@localhost/stock_db
```

### 使用 Massive 获取多个股票

```bash
python scripts/ingest_data.py \
    --provider massive \
    --universe tech \
    --start-date 2026-02-17
```

## API 配置

在 `.env` 文件中设置以下变量：

```env
MASSIVE_API_KEY=your_api_key_here
MASSIVE_BASE_URL=https://api.massive.com
```

## 已知限制

### 1. 数据访问限制

你的 API 密钥的计划似乎只支持：
- ✅ 最近的市场数据（最后 30-60 天）
- ✅ 分红数据（全历史）
- ❌ 历史 OHLCV 数据（2015-2023）

### 2. 拆股端点

拆股端点需要进一步调查以确定正确的参数格式。

## 建议

### 1. 历史数据补充

对于历史数据（2015-2023），建议：
- 使用 Yahoo Finance 作为备用数据源
- 在 `ingest_data.py` 中实现多源数据融合
- 优先使用 Massive 的最近数据，Yahoo Finance 的历史数据

### 2. 数据收集策略

建议的数据收集策略：
1. 从今天开始使用 Massive API 收集实时数据
2. 使用 Yahoo Finance 补充 2015-2023 的历史数据
3. 定期更新最近的数据以保持时效性

### 3. 升级 API 计划

如果需要完整的历史数据，考虑升级 Massive API 计划以获得：
- 完整的历史数据访问
- 更高的 API 速率限制
- 实时数据流

## 文件结构

```
src/etl/
├── data_providers.py          # 数据提供者实现（已更新）
├── pipelines.py               # 数据管道
└── ...

scripts/
├── ingest_data.py             # 数据摄取脚本（已更新）
└── ...

src/
├── config.py                  # 配置管理（已更新）
└── ...
```

## 故障排除

### 问题：403 Unauthorized 错误

**原因：** 你的 API 计划不包括所请求日期范围的数据

**解决方案：**
- 使用最近的日期（最后 30-60 天）
- 或升级 API 计划以获得历史数据访问

### 问题：400 Bad Request 错误

**原因：** 参数格式不正确

**解决方案：**
- 检查日期格式 (YYYY-MM-DD)
- 验证 API 密钥是否正确
- 查看 API 文档以了解正确的参数格式

### 问题：连接超时

**原因：** 网络问题或 API 服务不可用

**解决方案：**
- 检查网络连接
- 验证 API 端点是否可访问
- 查看 Massive API 状态页面

## 相关文档

- [Massive API 文档](https://massive.com/docs/rest/stocks/overview)
- [Massive API Quickstart](https://massive.com/docs/rest/quickstart)
- [Custom Bars (OHLC) 端点](https://massive.com/docs/rest/stocks/aggregates/custom-bars)

## 更新日志

### 2026-03-19

- ✅ 实现 `MassiveDataProvider` 类
- ✅ 实现日线数据获取
- ✅ 实现分红数据获取
- ✅ 实现拆股数据获取
- ✅ 更新工厂函数以支持 Massive 提供者
- ✅ 更新命令行工具以支持 Massive 选项
- ✅ 更新配置管理以支持 Massive API 密钥
- ✅ 文档化 API 限制和建议
