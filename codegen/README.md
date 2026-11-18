# codegen — 元模板代码生成

你写**元模板**（jinja2），每个新模块写一份**规格文件**（TOML），生成器按模板产出代码。

```bash
uv run python scripts/codegen.py codegen/specs/<模块>.toml --dry-run   # 先看会生成哪些文件
uv run python scripts/codegen.py codegen/specs/<模块>.toml             # 生成（已存在的文件不会覆盖）
uv run python scripts/codegen.py codegen/specs/<模块>.toml --force     # 覆盖
```

## 目录

```
codegen/
├─ templates/<模板集>/      # 一套元模板；目录结构 = 输出到项目里的位置
│  └─ src/domain/entity/{{ snake_name }}.py.j2   # 文件名、目录名也是模板，去掉 .j2 后缀
└─ specs/<模块>.toml        # 每个模块一份规格
```

`templates/example/` + `specs/example.toml` 只是演示机制，写好自己的模板集后可以删掉。

## 模板里能用的变量

规格文件整个就是上下文，另外有 `[module] name` 时自动推导：

| 变量 | 例（name = "user_group"） |
|---|---|
| `class_name` | `UserGroup` |
| `snake_name` | `user_group` |
| `kebab_name` | `user-group` |
| `plural_name` | `user_groups` |
| `module` | 规格里的 `[module]` 表（`module.table`、`module.comment` …） |
| `fields` | 规格里的 `[[fields]]` 列表（字段名、类型等自由定义，由模板解释） |

过滤器：`snake`、`pascal`、`camel`、`kebab`、`plural`，例如 `{{ "UserGroup" | snake }}`。
未定义的变量会直接报错（`StrictUndefined`），模板里的拼写错误不会悄悄生成空字符串。

## 写模板时的项目约定

- `src/` 内部用**相对导入**（`from ..domain.entity import ...`），不要写 `from src...`（架构测试会检查）
- 分层：endpoint → usercase → service → domain 仓储接口；DAO 用 `XxxDO`，实现 `to_entity` / `to_do`
- **Swagger**：生成的 router 写 `APIRouter(prefix=..., tags=["{{ snake_name }}"])`，并在
  `src/presentation/openapi.py` 的 `OPENAPI_TAGS` 加一条分组说明；endpoint 的 docstring 会显示为接口描述，
  返回值标注 ResponseDTO 类型，Swagger 才有响应结构
- 新表：生成 `XxxDO` 后执行 `uv run alembic revision --autogenerate -m "..."`，再 `uv run python scripts/gen_db_doc.py`
- 生成的 `.py` 会自动 `ruff check --fix` + `ruff format`
