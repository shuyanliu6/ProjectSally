# 📝 代码讲解：config.py

## 文件目的

`config.py` 是**全局配置管理中心**。它的作用是：

1. **集中管理所有配置** - 数据库、API 密钥、日志等
2. **从环境变量读取** - 敏感信息不硬编码在代码中
3. **提供默认值** - 如果环境变量没有设置，使用默认值
4. **验证配置** - 确保配置有效

---

## 代码逐行讲解

### 第 1-8 行：导入和文档

```python
"""
Configuration management for Project Sally.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from datetime import datetime
```

**解释：**
- `Optional` - 表示某个值可以是某类型或 None
- `BaseSettings` - Pydantic 提供的基类，自动从环境变量读取配置
- `Field` - 定义配置字段的元数据（默认值、别名等）

**为什么用 Pydantic？**
- 自动验证数据类型（如果你设置 `db_port="abc"`，会报错）
- 自动从环境变量读取
- 代码简洁清晰

---

### 第 11-19 行：数据库配置

```python
class Config(BaseSettings):
    """Application configuration from environment variables."""

    # Database Configuration
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_user: str = Field(default="stock_user", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_name: str = Field(default="stock_picking_system", alias="DB_NAME")
```

**逐行讲解：**

```python
db_host: str = Field(default="localhost", alias="DB_HOST")
```

- `db_host` - Python 属性名（代码中使用）
- `: str` - 类型注解（必须是字符串）
- `default="localhost"` - 默认值（如果环境变量没设置）
- `alias="DB_HOST"` - 环境变量名（在 `.env` 或系统环境中的名称）

**使用示例：**

```bash
# 在 .env 文件或系统环境中设置
export DB_HOST=database
export DB_PORT=5432
export DB_USER=stock_user
export DB_PASSWORD=secure_password_123
export DB_NAME=stock_picking_system
```

**在代码中使用：**

```python
config = get_config()
print(config.db_host)      # 输出：database
print(config.db_port)      # 输出：5432
print(config.db_user)      # 输出：stock_user
```

**关键点：**
- 如果环境变量设置了，使用环境变量的值
- 如果没设置，使用 `default` 的值
- 这样可以在不修改代码的情况下改变配置

---

### 第 21-25 行：数据提供者配置

```python
    # Data Provider Configuration
    data_provider: str = Field(default="yfinance", alias="DATA_PROVIDER")
    eodhd_api_key: Optional[str] = Field(default=None, alias="EODHD_API_KEY")
    polygon_api_key: Optional[str] = Field(default=None, alias="POLYGON_API_KEY")
    alpha_vantage_api_key: Optional[str] = Field(default=None, alias="ALPHA_VANTAGE_API_KEY")
```

**讲解：**

```python
data_provider: str = Field(default="yfinance", alias="DATA_PROVIDER")
```
- 选择使用哪个数据提供者（yfinance、polygon、eodhd 等）
- 默认是 yfinance

```python
polygon_api_key: Optional[str] = Field(default=None, alias="POLYGON_API_KEY")
```
- `Optional[str]` - 可以是字符串或 None
- `default=None` - 如果没设置，就是 None
- 这样可以支持多个数据提供者，每个都有自己的 API 密钥

**使用示例：**

```bash
# 设置使用 Polygon.io
export DATA_PROVIDER=polygon
export POLYGON_API_KEY=your_api_key_here
```

**在代码中使用：**

```python
config = get_config()
if config.data_provider == "polygon":
    provider = PolygonProvider(api_key=config.polygon_api_key)
elif config.data_provider == "yfinance":
    provider = YFinanceProvider()
```

---

### 第 27-34 行：应用配置

```python
    # Application Configuration
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=True, alias="DEBUG")

    # Data Configuration
    start_date: str = Field(default="2015-01-01", alias="START_DATE")
    end_date: str = Field(default="2024-12-31", alias="END_DATE")
```

**讲解：**

```python
environment: str = Field(default="development", alias="ENVIRONMENT")
```
- 运行环境：development（开发）或 production（生产）
- 用来区分开发和生产环境的行为

```python
log_level: str = Field(default="INFO", alias="LOG_LEVEL")
```
- 日志级别：DEBUG、INFO、WARNING、ERROR
- 控制日志的详细程度

```python
debug: bool = Field(default=True, alias="DEBUG")
```
- 是否启用调试模式
- 在生产环境应该设置为 False

```python
start_date: str = Field(default="2015-01-01", alias="START_DATE")
end_date: str = Field(default="2024-12-31", alias="END_DATE")
```
- 数据摄入的时间范围
- 默认从 2015 年到 2024 年

---

### 第 36-38 行：Pydantic 配置

```python
    class Config:
        env_file = ".env"
        case_sensitive = False
```

**讲解：**

```python
env_file = ".env"
```
- 从 `.env` 文件读取环境变量
- `.env` 文件格式：`KEY=value`

```python
case_sensitive = False
```
- 环境变量名不区分大小写
- `DB_HOST`、`db_host`、`Db_Host` 都可以

---

### 第 40-46 行：数据库 URL 属性

```python
    @property
    def database_url(self) -> str:
        """Generate database connection URL."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )
```

**讲解：**

`@property` 是 Python 装饰器，让你可以像访问属性一样调用方法。

**作用：** 生成数据库连接 URL

**示例：**

```python
config = get_config()
print(config.database_url)
# 输出：postgresql://stock_user:secure_password_123@database:5432/stock_picking_system
```

**为什么要这样做？**
- 不用每次都手动拼接 URL
- 如果配置改变，URL 自动更新
- 代码更清晰

---

### 第 48-56 行：环境检查属性

```python
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
```

**讲解：**

```python
@property
def is_production(self) -> bool:
    return self.environment.lower() == "production"
```

- 检查是否在生产环境
- `.lower()` - 转换为小写（防止大小写问题）

**使用示例：**

```python
config = get_config()
if config.is_production:
    # 生产环境的行为
    logger.setLevel(logging.WARNING)
else:
    # 开发环境的行为
    logger.setLevel(logging.DEBUG)
```

---

### 第 59-61 行：工厂函数

```python
def get_config() -> Config:
    """Get application configuration."""
    return Config()
```

**讲解：**

- 这是一个**工厂函数**
- 每次调用都返回一个新的 Config 实例
- 确保配置始终是最新的

**使用示例：**

```python
# 在其他文件中使用
from src.config import get_config

config = get_config()
print(config.db_host)
```

---

## 完整的使用流程

### 1. 设置环境变量（`.env` 文件）

```bash
# 数据库配置
DB_HOST=database
DB_PORT=5432
DB_USER=stock_user
DB_PASSWORD=secure_password_123
DB_NAME=stock_picking_system

# 数据提供者配置
DATA_PROVIDER=polygon
POLYGON_API_KEY=your_polygon_api_key

# 应用配置
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=True

# 数据配置
START_DATE=2015-01-01
END_DATE=2024-12-31
```

### 2. 在代码中使用

```python
from src.config import get_config

config = get_config()

# 使用数据库配置
db_url = config.database_url
print(db_url)  # postgresql://stock_user:...@database:5432/stock_picking_system

# 使用数据提供者配置
if config.data_provider == "polygon":
    api_key = config.polygon_api_key
    # 初始化 Polygon 提供者

# 使用应用配置
if config.is_development:
    print("Running in development mode")
    
# 使用数据配置
print(f"Fetching data from {config.start_date} to {config.end_date}")
```

---

## 设计优点

### ✅ 优点

1. **集中管理** - 所有配置在一个地方
2. **环境隔离** - 不同环境使用不同配置
3. **安全** - 敏感信息不硬编码
4. **灵活** - 支持多个数据提供者
5. **类型安全** - Pydantic 自动验证类型
6. **易于测试** - 可以轻松注入测试配置

---

## 改进建议

### 可能的改进

1. **配置验证** - 某些配置组合可能无效
   ```python
   @validator('data_provider')
   def validate_provider(cls, v):
       valid_providers = ['yfinance', 'polygon', 'eodhd']
       if v not in valid_providers:
           raise ValueError(f'Invalid provider: {v}')
       return v
   ```

2. **API 密钥验证** - 确保选择的提供者有 API 密钥
   ```python
   @root_validator
   def validate_api_keys(cls, values):
       provider = values.get('data_provider')
       if provider == 'polygon' and not values.get('polygon_api_key'):
           raise ValueError('polygon_api_key required for polygon provider')
       return values
   ```

3. **日期范围验证** - 确保 start_date < end_date
   ```python
   @validator('end_date')
   def validate_dates(cls, v, values):
       if 'start_date' in values and v < values['start_date']:
           raise ValueError('end_date must be after start_date')
       return v
   ```

---

## 总结

**config.py 的核心思想：**

> **将所有配置集中管理，从环境变量读取，提供类型安全和验证。**

**关键特性：**
- 从环境变量读取
- 提供默认值
- 类型验证
- 支持多个数据提供者
- 环境区分（开发/生产）

---

## 下一步

现在你理解了 `config.py`。接下来我们讲解：

1. **database/connection.py** - 数据库连接
2. **database/schema.py** - 表结构定义
3. **etl/data_providers.py** - 数据源适配（然后集成 Polygon.io）
4. **etl/pipelines.py** - ETL 管道

你有问题或建议吗？
