# 📝 代码讲解：database/connection.py

## 文件目的

`connection.py` 是**数据库连接管理中心**。它的作用是：

1. **创建数据库引擎** - 连接到 PostgreSQL
2. **管理数据库会话** - 提供数据库操作的上下文
3. **初始化数据库** - 创建所有表
4. **启用 TimescaleDB** - 激活时间序列优化

---

## 核心概念：SQLAlchemy

在讲解代码之前，需要理解 SQLAlchemy 的几个核心概念：

### 1. **Engine（引擎）**
- 代表与数据库的连接池
- 负责执行 SQL 语句
- 管理连接的生命周期

### 2. **Session（会话）**
- 代表一个数据库操作的上下文
- 类似于一个"工作单元"
- 所有数据库操作都在 Session 中进行

### 3. **ORM（对象关系映射）**
- 将数据库表映射为 Python 类
- 将数据库行映射为 Python 对象
- 自动处理 SQL 生成

**类比：**
```
Engine = 电话线（连接到数据库）
Session = 一次通话（一个操作周期）
ORM = 语言翻译（Python 对象 ↔ SQL 语句）
```

---

## 代码逐行讲解

### 第 1-7 行：导入

```python
"""Database connection management."""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from src.config import get_config
from typing import Generator
```

**讲解：**

```python
from sqlalchemy import create_engine, event, text
```
- `create_engine` - 创建数据库引擎
- `event` - 事件监听（用于监听数据库连接事件）
- `text` - 执行原始 SQL（当 ORM 不够用时）

```python
from sqlalchemy.orm import sessionmaker, Session
```
- `sessionmaker` - 会话工厂（用来创建 Session）
- `Session` - 会话类型

```python
from sqlalchemy.pool import NullPool
```
- `NullPool` - 禁用连接池
- 简化开发环境的配置（生产环境应该使用连接池）

```python
from typing import Generator
```
- `Generator` - 生成器类型（用于类型注解）

---

### 第 9 行：全局配置

```python
config = get_config()
```

**讲解：**
- 在模块加载时获取配置
- 后续函数可以使用这个配置

---

### 第 12-33 行：创建数据库引擎

```python
def get_engine():
    """Create and return SQLAlchemy engine."""
    engine = create_engine(
        config.database_url,
        echo=config.debug,
        poolclass=NullPool,
    )

    # Enable TimescaleDB extension on connection
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Enable TimescaleDB extension when connecting."""
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
            dbapi_conn.commit()
        except Exception as e:
            print(f"Warning: Could not enable TimescaleDB extension: {e}")
        finally:
            cursor.close()

    return engine
```

**详细讲解：**

#### 第 14-18 行：创建引擎

```python
engine = create_engine(
    config.database_url,
    echo=config.debug,
    poolclass=NullPool,
)
```

**参数讲解：**

```python
config.database_url
```
- 数据库连接 URL
- 格式：`postgresql://user:password@host:port/database`
- 例如：`postgresql://stock_user:secure_password_123@database:5432/stock_picking_system`

```python
echo=config.debug
```
- 如果 `config.debug=True`，打印所有 SQL 语句
- 用于调试，看看 SQLAlchemy 生成了什么 SQL

**输出示例：**
```
SELECT assets.id, assets.symbol, assets.name 
FROM assets 
WHERE assets.symbol = ?
```

```python
poolclass=NullPool
```
- 禁用连接池
- 每次需要连接时创建新连接，用完后关闭
- 简化开发环境（生产环境应该使用连接池以提高性能）

#### 第 20-31 行：监听连接事件

```python
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Enable TimescaleDB extension when connecting."""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        dbapi_conn.commit()
    except Exception as e:
        print(f"Warning: Could not enable TimescaleDB extension: {e}")
    finally:
        cursor.close()
```

**讲解：**

```python
@event.listens_for(engine, "connect")
```
- 装饰器，监听 engine 的 "connect" 事件
- 每当建立新连接时，自动调用下面的函数

```python
def receive_connect(dbapi_conn, connection_record):
```
- `dbapi_conn` - 原始数据库连接对象
- `connection_record` - 连接记录

```python
cursor = dbapi_conn.cursor()
```
- 创建游标（用来执行 SQL）

```python
cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
```
- 执行 SQL 命令
- `CREATE EXTENSION IF NOT EXISTS` - 如果扩展不存在，创建它
- 这样启用 TimescaleDB 的时间序列优化

```python
dbapi_conn.commit()
```
- 提交事务（确保命令执行）

```python
except Exception as e:
    print(f"Warning: Could not enable TimescaleDB extension: {e}")
finally:
    cursor.close()
```
- 如果出错，打印警告但不中断程序
- 无论成功还是失败，都关闭游标

**为什么这样做？**
- TimescaleDB 是 PostgreSQL 的扩展
- 需要在连接时启用
- 这样所有连接都自动启用了 TimescaleDB

---

### 第 37 行：创建会话工厂

```python
SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
```

**讲解：**

```python
sessionmaker(bind=get_engine(), expire_on_commit=False)
```
- 创建一个会话工厂
- `bind=get_engine()` - 绑定到我们的引擎
- `expire_on_commit=False` - 提交后不过期对象

**`expire_on_commit=False` 的意思：**

```python
# expire_on_commit=True（默认）
session.add(asset)
session.commit()
print(asset.name)  # 需要重新查询数据库

# expire_on_commit=False（我们的设置）
session.add(asset)
session.commit()
print(asset.name)  # 直接使用内存中的对象，不需要重新查询
```

**为什么设置为 False？**
- 减少数据库查询
- 提高性能
- 对于我们的用途足够了

---

### 第 40-46 行：获取会话

```python
def get_session() -> Generator[Session, None, None]:
    """Get database session for dependency injection."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

**讲解：**

```python
def get_session() -> Generator[Session, None, None]:
```
- 返回类型是 `Generator[Session, None, None]`
- 这是一个**生成器函数**（使用 `yield`）

**为什么用生成器？**
- 确保会话在使用后被关闭
- 自动资源管理

**使用示例：**

```python
# 方式 1：直接使用
for session in get_session():
    # 使用 session
    assets = session.query(Asset).all()
    # 函数结束时自动关闭 session

# 方式 2：在 FastAPI 中使用（依赖注入）
@app.get("/assets")
def get_assets(session: Session = Depends(get_session)):
    return session.query(Asset).all()
```

**执行流程：**

```python
session = SessionLocal()  # 创建会话
try:
    yield session  # 返回会话给调用者
finally:
    session.close()  # 调用者用完后，自动关闭
```

**类比：**
```
try-finally = 借书-还书
yield = 把书给你
finally = 你用完后自动还回来
```

---

### 第 49-55 行：初始化数据库

```python
def init_db():
    """Initialize database with all tables."""
    from src.database.schema import Base

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")
```

**讲解：**

```python
from src.database.schema import Base
```
- 导入 Base（所有 ORM 模型的基类）
- 延迟导入（避免循环导入）

```python
Base.metadata.create_all(bind=engine)
```
- `metadata` - 所有表的元数据
- `create_all()` - 创建所有表
- 如果表已存在，不会重复创建

**执行流程：**
1. 扫描所有继承自 Base 的模型类
2. 为每个模型生成 CREATE TABLE 语句
3. 执行 SQL 创建表

**使用示例：**

```bash
# 在 Docker 容器中运行
docker-compose exec app python scripts/init_db.py --create
```

---

### 第 58-64 行：删除数据库

```python
def drop_db():
    """Drop all tables (use with caution!)."""
    from src.database.schema import Base

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print("Database dropped successfully!")
```

**讲解：**

```python
Base.metadata.drop_all(bind=engine)
```
- 删除所有表
- **危险操作！** 会丢失所有数据

**使用场景：**
- 开发环境重置
- 测试后清理
- 重新开始

**使用示例：**

```bash
# 删除所有表（谨慎使用！）
docker-compose exec app python -c "from src.database.connection import drop_db; drop_db()"
```

---

## 完整的数据库操作流程

### 1. 初始化（第一次运行）

```python
from src.database.connection import init_db

# 创建所有表
init_db()
```

### 2. 获取会话并操作

```python
from src.database.connection import get_session
from src.database.schema import Asset

# 获取会话
for session in get_session():
    # 创建新资产
    asset = Asset(symbol="AAPL", name="Apple Inc.")
    session.add(asset)
    session.commit()
    
    # 查询资产
    assets = session.query(Asset).all()
    print(assets)
    
    # 会话自动关闭
```

### 3. 在 FastAPI 中使用

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from src.database.connection import get_session
from src.database.schema import Asset

app = FastAPI()

@app.get("/assets")
def list_assets(session: Session = Depends(get_session)):
    return session.query(Asset).all()
```

---

## 设计优点

### ✅ 优点

1. **集中管理** - 所有数据库连接在一个地方
2. **自动资源管理** - 会话自动关闭
3. **TimescaleDB 自动启用** - 不需要手动配置
4. **灵活** - 支持依赖注入
5. **调试友好** - `echo=debug` 可以看到 SQL

---

## 可能的问题和改进

### 问题 1：连接池

**当前：** 使用 `NullPool`（每次创建新连接）
**问题：** 性能不好（频繁创建/销毁连接）
**改进：** 在生产环境使用连接池

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    config.database_url,
    poolclass=QueuePool,
    pool_size=10,  # 保持 10 个连接
    max_overflow=20,  # 最多额外 20 个连接
)
```

### 问题 2：错误处理

**当前：** TimescaleDB 启用失败只打印警告
**改进：** 可以记录到日志或监控系统

```python
import logging

logger = logging.getLogger(__name__)

try:
    cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    dbapi_conn.commit()
except Exception as e:
    logger.warning(f"Could not enable TimescaleDB: {e}")
```

### 问题 3：会话管理

**当前：** 每次调用 `get_session()` 都创建新会话
**改进：** 可以使用上下文管理器简化

```python
from contextlib import contextmanager

@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# 使用
with get_db_session() as session:
    assets = session.query(Asset).all()
```

---

## 总结

**connection.py 的核心思想：**

> **集中管理数据库连接，提供会话管理，自动启用 TimescaleDB。**

**关键特性：**
- SQLAlchemy 引擎管理
- 事件监听自动启用 TimescaleDB
- 生成器函数自动管理会话生命周期
- 支持依赖注入

---

## 下一步

现在你理解了数据库连接层。接下来讲解：

1. **database/schema.py** - 表结构定义（ORM 模型）
2. **etl/data_providers.py** - 数据源适配
3. **etl/pipelines.py** - ETL 管道

你有问题或建议吗？
