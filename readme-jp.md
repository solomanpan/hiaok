# hiaok — 軽量パーミッションセンター

[English](readme-en.md) · **日本語** · [中文](readme-zh.md) · アーキテクチャ設計書（英語）：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

DDD 4 層 + イベント駆動 + 書き込みはマスター・読み取りはスレーブ。Python 3.12 · FastAPI · SQLAlchemy 2 (asyncpg) · Alembic · Expression · Redis（キャッシュ / Streams）· Kafka

組織・テナント・ユーザー・ユーザーグループ・プロジェクト・ロール・権限・メニュー・部門・従業員・システム設定・監査ログの管理 API に加え、ログイン認証（Bearer トークン + 権限コード）と多言語のエラーメッセージ（en / zh / ja）を提供します。

本書はテーマ別に構成されています。

1. [クイックスタート](#1-クイックスタート)
2. [この DDD フレームワークの使い方](#2-この-ddd-フレームワークの使い方)
3. [認可の仕組み](#3-認可の仕組み)
4. [Kafka の使い方](#4-kafka-の使い方)
5. [Redis の使い方](#5-redis-の使い方)
6. [国際化（i18n）](#6-国際化i18n)
7. [API の規約](#7-api-の規約)
8. [設定リファレンス](#8-設定リファレンス)
9. [テストと注意事項](#9-テストと注意事項)

---

## 1. クイックスタート

```bash
uv sync
docker compose up -d postgres-master postgres-slave redis   # インフラのみ起動
uv run alembic upgrade head                                  # マイグレーションは常にマスターへ
uv run hiaok                                                 # API  http://localhost:8000/docs
uv run hiaok worker                                          # イベントコンシューマ（APP_CONSUME_EVENTS=false のとき必要）

docker compose up -d --build                                 # 全コンテナ：マスター・スレーブ + redis + migrate + api + worker
docker compose --profile kafka up -d --build                 # Kafka も起動（APP_BROKER=kafka を設定）
```

- 設定：実際の環境変数 `APP_ENV` でプロファイルを選びます。`.env`、続いて `.env.<APP_ENV>` を読み込み、実際の環境変数が優先されます。全項目は[設定リファレンス](#8-設定リファレンス)を参照してください。
- マイグレーション：`uv run alembic revision --autogenerate -m "..."`。トリガーは使いません。`update_time` は SQLAlchemy の `onupdate=func.now()` が UPDATE ごとに書き込みます。テーブルを変更したら `uv run python scripts/gen_db_doc.py` で [`db.properties.md`](db.properties.md) を再生成します（古くなっていればテストが失敗します）。
- 初期状態ではユーザーがいません。まず `AUTH_ENABLED=false` で起動し、組織・ロール・管理者を作成してから認証を有効にしてください（[認可の仕組み](#3-認可の仕組み)参照）。

## 2. この DDD フレームワークの使い方

### 2.1 レイヤーと依存の向き

```
presentation → application → domain ← infrastructure          （どの層も hiaok_core を使える）
```

```
src/                              # 業務パッケージ（src 自体がパッケージ）：内部は相対インポート、tests / scripts は from src.domain ...
├─ main.py                        # CLI `hiaok`（API）| `hiaok worker`（コンシューマ）；create_app() / lifespan
├─ domain/                        # hiaok_core にのみ依存し、フレームワークに依存しない
│  ├─ entity/                     # エンティティと集約ルート（create は Result を返しイベントを記録）；event.py = 全ドメインイベント
│  ├─ vo/  enum/                  # 値オブジェクト（生成時に検証）、列挙型
│  ├─ service/                    # ドメインサービス：tree（ツリー構築 / 循環防止）、authority（権限の和集合）
│  └─ repository/                 # リポジトリのインターフェース（Protocol）+ Page / PageQuery
├─ application/
│  ├─ config/                     # app / auth / database / redis / kafka 設定（pydantic-settings）
│  ├─ model/                      # アプリケーションモデル：XxxModel(from_domain/to_domain)、CreateXxx、UpdateXxx
│  ├─ service/                    # @master / @slave アプリケーションサービス（トランザクション境界）
│  └─ usecase/                    # カリー化されたユースケース + イベントハンドラ + 書き込みコマンド処理
├─ infrastructure/
│  ├─ database/ do/ dao/ repository/   # マスター/スレーブのエンジン、テーブルオブジェクト XxxDO、DAO（to_entity / to_do）、リポジトリ実装
│  ├─ messaging/                  # EventBus：Redis Streams / Kafka / インメモリ；topics.py = Kafka のルーティング
│  ├─ cache/ security/ http/      # Cache（Redis / メモリ）、PasswordHasher（scrypt）、HttpClient（httpx）
│  └─ resources.py  migrations/   # プロセス共通リソース；Alembic
└─ presentation/
   ├─ endpoint/                   # ルート：リクエスト DTO + 注入されたユースケース -> レスポンス DTO
   ├─ schema/                     # DTO（pydantic、camelCase）とアプリケーションモデルの相互変換
   ├─ dependency/                 # 依存性注入：resources -> service -> usecase；認可ガード
   └─ exception.py middleware.py i18n.py messages.py security.py openapi.py
```

**hiaok-core** は独立したリポジトリ <https://github.com/solomanpan/hiaok-core> です（facade インターフェース、例外、JSON / fp ユーティリティ、リクエストコンテキスト）。uv の Git 依存としてタグ固定で取り込みます。更新するには `pyproject.toml [tool.uv.sources]` のタグを変更し、`uv lock --upgrade-package hiaok-core` を実行します。両方を同時に開発するときはローカルの `path` 依存に一時的に切り替えられます。コミット前にタグへ戻してください。

次のルールは `tests/unit/test_architecture.py` にあり、違反するとテストが失敗します：層の依存方向、各層に置けるサブパッケージ、`port / PO / mapper` の命名禁止、データオブジェクトは `XxxDO`、すべての DAO に `to_entity / to_do`、業務エラーはエラーカタログ由来、`src` 内は相対インポート。

### 2.2 リクエストの流れ（ユーザー登録の例）

```
POST /v1/api/hiaok/user/add   {"requestId": "...", "reqInfo": {"orgUuid": "...", ...}}
  ApiRequest[UserRegisterRequest].req_info.to_command()     # schema: リクエスト DTO -> RegisterUser
  usecase: RegisterUserDep                                  # dependency: register_user(users, tenants, roles, hasher)
  register_user(...)(cmd)                                   # usecase: カリー化、最後の引数がリクエストデータ
    RawPassword.create → tenants.get(@slave) → roles.list_by_uuids(@slave) → hash
    → users.register(@master)                               # service: マスターのトランザクションを開く
        cmd.to_domain(uuid, hash) → User.register(...)      # domain: 検証 + イベント記録
        repo.save → DAO.to_do（user / user_detail / user_role）
        commit → after_commit: EntityCreated, UserRegistered を発行
    .map(UserModel.from_domain)
  reply(result, UserResponse.of)                            # -> {"code": 0, "msg": "success", "resultInfo": {...}}
                                                            #    Error -> {"code": 400/403/404/409, "msg": ..., "errorCode": ...}
```

### 2.3 集約（`Xxx`）を追加する

1. **ドメイン**：`domain/entity/xxx.py` — `create(...)` は `Result[Xxx, DomainError]` を返してイベントを記録します。業務エラーは同じファイルの `XxxErrors(ErrorCatalog)` に書きます。`domain/repository` にリポジトリのインターフェースを追加します。
2. **テーブル**：`infrastructure/do/xxx.py`（`XxxDO`）→ `alembic revision --autogenerate` → `scripts/gen_db_doc.py`。
3. **DAO / リポジトリ**：`XxxDao(EntityDao[XxxDO, Xxx])` で `to_entity` / `to_do` を実装します。単一テーブルの集約のリポジトリは `SqlRepository(db, XxxDao(db))` だけで済みます。
4. **アプリケーション**：`application/model/xxx.py`（`XxxModel` / `CreateXxx` / `UpdateXxx`）+ `application/service`（`CrudService` を継承。書き込みは `@master`、読み取りは `@slave`）。
5. **プレゼンテーション**：`presentation/schema/xxx.py`（DTO）+ `presentation/dependency` にサービスとユースケースを登録 + `presentation/endpoint/xxx.py` にルート。
6. **書き込みハンドラの登録**：`build_write_handlers`（`presentation/dependency/command.py`）にハンドラを追加します（標準 CRUD は `_crud(...)` の 1 行）。`test_write_handlers.py` がエンドポイントとハンドラの 1 対 1 対応を検査します。
7. **Kafka のルーティング**：`infrastructure/messaging/topics.py` で新しいエンティティとイベントにトピックを割り当てます（忘れるとテストが失敗します）。
8. **認可と翻訳**：ルートに `dependencies=[has_permission("xxx:add")]` を付け、エラーメッセージを `presentation/messages.py` に追加します（翻訳が無ければテストが失敗します）。

> **すべてのルートに認可があります**（`<resource>:<endpoint>`、例 `user:add`。`user:*` はリソース全体、`*` はプラットフォーム管理者で全組織を操作可）。公開ルート：`auth/login`、`auth/captcha`、`user/register`（キャプチャ保護。`roleUuids` には `user:assign-roles` が必要）、`/health`。新規組織の `ORG_ADMIN` ロールには組織内の全リソースの `<resource>:*` が付与されます（`*` ではない）。初回は `AUTH_ENABLED=false` で組織・管理者を作成するか、`AUTH_PLATFORM_ORG_UUID` の `*` ユーザーでログインしてください。


`codegen/` のメタテンプレート（jinja2）と仕様ファイルから、この骨格を生成することもできます。[codegen/README.md](codegen/README.md) を参照してください。

### 2.4 各層の書き方

**エンドポイント**：リクエスト型とレスポンス型を関数シグネチャに書くと、FastAPI がそれで検証し Swagger を生成します。すべて `POST` で、成否は `code` で表すため `status_code` は不要です。

```python
@router.post("/add", dependencies=[has_permission("role:add")])
async def create_role(
    request: ApiRequest[RoleCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Role", request.request_id, info.org_uuid, info.to_command()))
```

**依存性注入**（`presentation/dependency/`）：すべて FastAPI の `Depends` で、3 段構成です。`resources.py`（`app.state` 上のプロセス共通リソース）→ `service.py`（リポジトリ実装をアプリケーションサービスへ注入）→ `usecase.py`（サービスをユースケースへ注入）。エンドポイントは必要なユースケースだけを宣言します（例：`usecase: RegisterUserDep`）。標準 CRUD は `crud_usecases(service, Model.from_domain)` でまとめて登録し、複合ユースケースは個別に登録します。

**ユースケース**：カリー化された関数で、依存が先、リクエストデータが最後です。`AsyncResult` のチェーン（`bind / map / ensure`）で組み立て、`Result` を返し、業務例外は投げません。

**エラーカタログ**：業務エラーは種別 + コード + メッセージテンプレートを 1 か所で宣言します。`conflict(...)` をその場で組み立てないでください。

```python
class RoleErrors(ErrorCatalog):
    system_role = ErrorSpec.conflict("system_role", "system role '{code}' cannot be deleted")


return RoleErrors.system_role.err(code=self.role_code)  # Result スタイル
RoleErrors.system_role.raise_(code=...)  # 例外にするしかないとき
```

複数の集約にまたがるルールは `application/usecase/errors.py`（`UseCaseErrors`）にあります。汎用の `not_found(entity, id)` はそのまま使います。

**書き込みはマスター、読み取りはスレーブ**：

```python
class RoleService(CrudService[Role]):
    @slave                      # 読み取り：スレーブ、読み取り専用トランザクション
    async def get(...): ...

    @master                     # 書き込み：マスター；Ok -> commit、Error/例外 -> rollback
    async def grant_permissions(...): ...
```

| 状況 | 動作 |
|---|---|
| 最も外側のデコレート済み呼び出し | セッション（マスターまたはスレーブ）を開く |
| `@master` の中の `@slave` | マスターのセッションに参加：自分の書き込みを読める |
| `@slave` の中の `@master` | `DataSourceRoutingError` を送出 |
| `Error(...)` を返す | ルートスコープだけが決める：ロールバックし、`after_commit` は実行しない |
| `@slave` の中で書き込む | ドライバが読み取り専用のため DB が拒否 |
| ドメインイベント | ルートトランザクションのコミット成功後にのみ発行 |

複数の集約をアトミックに書く処理はオーケストレーションサービスに置きます：`ProvisioningService.provision`（組織 + 詳細 + デフォルトテナント + ORG_ADMIN + デフォルト設定）、`OnboardingService.onboard`（入社 + アカウント開設 + 紐付け）。外側の `@master` が 1 つのトランザクションとなり、内側のサービスの `@master` は自動的に参加します。リポジトリ / DAO は自分でセッションを開きません。デコレート済みメソッドの外で呼ぶと `NoActiveScopeError` になります。同じスコープ内で複数のリポジトリ呼び出しを `asyncio.gather` しないでください（AsyncSession を共有しています）。

**テストデータ**：`tests/factories.py`（polyfactory）：`RoleFactory.build(...)`、`PermissionFactory.batch(3)`。ファクトリはエンティティを直接構築します（検証もイベントもなし）。検証やイベント自体をテストするときは集約の `create` / `register` を使います。

## 3. 認可の仕組み

### 3.1 フロー

```
POST /auth/login {orgUuid, tenantUuid, username, password}
  → ユーザー（有効）、パスワード（scrypt）、テナント（有効かつ期限内）を確認
  → ランダムなトークンを生成し、セッション {userUuid, orgUuid, tenantUuid} をキャッシュに保存（TTL = AUTH_SESSION_TTL_SECONDS、既定 2 時間）
  ← accessToken

以降のすべてのリクエスト：Authorization: Bearer <token>
  ミドルウェア  トークン → セッション → リクエストコンテキストを設定（operator = ユーザー uuid、org、tenant）；監査列 opr は自動的にログインユーザーになる
  ガード        has_permission("role:add") / has_role("admin") / authenticated()
                セッション → 権限（ユーザー → 有効なロール → 権限コード；ユーザーごとにキャッシュ）→ 判定 → 通過 / 401 / 403
```

トークンは情報を持たないランダム文字列で、キャッシュには SHA-256 だけを保存します。`/auth/logout` でセッションを削除すれば、トークンは即座に無効になります。

### 3.2 エンドポイントでの宣言

```python
@router.post(
    "/add", dependencies=[has_permission("role:add")]
)  # いずれかのコード；role:* は role:add を含み、* はすべてを含む
@router.post("/list", dependencies=[has_role("admin", "auditor")])  # いずれかのロール
@router.post("/me", dependencies=[authenticated()])  # ログイン済みであればよい
async def handler(principal: PrincipalDep): ...  # 呼び出し元を知りたいとき
```

- **権限コードの規約**：`<リソース>:<アクション>`（例：`role:grant-permissions`、`menu:move`）。アクションはルートと 1 対 1 で対応します。どのロールがどのコードを持つかは権限テーブルのデータなので、付与を変えてもコード変更は不要です。`has_permission` を優先し、`has_role` は「スーパー管理者」のような少数の場面に限ります。
- **テナント分離**：ボディの `reqInfo.orgUuid` が呼び出し元の組織でなければ 403 `org_mismatch` を返します。`AUTH_PLATFORM_ORG_UUID` で指定したプラットフォーム組織と、`*` を持つユーザーは組織をまたげます。
- **結果**：未ログイン / トークン無効・期限切れ → `code` 401（`unauthenticated`）、権限なし → 403（`permission_denied` / `role_denied`）。HTTP ステータスは他の業務エラーと同様 200 のままです。
- **スイッチ**：`AUTH_ENABLED=false` ではすべてのガードが通過し、`X-Operator` ヘッダーが操作者になります（ローカルデバッグ・初回セットアップ用）。
- **認証コード**（既定はオフ）：`AUTH_CAPTCHA_ENABLED=true` のとき、`POST /auth/login` と `POST /user/register` に `captchaId` と `captchaCode` が必要です。使い捨て画像は `POST /auth/captcha` で取得します（有効期間 `AUTH_CAPTCHA_TTL_SECONDS`、既定 120 秒。失敗すると無効になります）。
- **CORS**：`APP_CORS_ORIGINS`（カンマ区切り。例 `http://localhost:5173,tauri://localhost`）を設定すると、フロントエンド hiaok-web（Web / デスクトップ / モバイル）から API を呼べます。

### 3.3 権限とメニューの計算

権限 = ユーザー → 有効なロール → 権限コードの和集合。メニュー = 同じロール → メニューの和集合から、有効かつ表示可能なものだけを残してツリーにしたものです（`domain/service/authority.py`）。

- `/auth/me` は `roleCodes`、`permissionCodes`、メニューツリーを返します。フロントエンドはログイン後に一度呼んでサイドバーを描画します。**メニューはフロントエンドの表示を決めるだけで、API 呼び出しの可否は常にそのエンドポイント自身のガードが決めます。**
- ロールと権限コードはユーザーごとに `AUTH_AUTHORITY_TTL_SECONDS`（既定 60 秒）キャッシュされます。ユーザー・ユーザーグループ・ロール・権限の作成 / 更新 / 削除イベントと、ロールへの権限付与・メニュー割り当てイベントは、その組織のキャッシュ全体を即座に無効にします（[Redis の使い方](#5-redis-の使い方)参照）。メニューツリーはキャッシュせず、`/auth/me` は毎回 DB を参照します。

### 3.4 現状と今後

- 現在ガードが付いているのは `role`、`menu`、`/auth/*` で、他のリソースにはまだありません。`tests/unit/presentation/test_security.py` の `UNGUARDED_YET` が未対応のリソースを列挙しており、ガードの無い新しいエンドポイントはテストを失敗させます。リソースにガードを付け終えたら、その集合から外してください。
- `/user/authorities` にはまだガードがなく、誰でも誰の権限でも照会できます。早めに追加してください。
- 最初の管理者は手作業で作成します（`AUTH_ENABLED=false` で起動して登録）。

## 4. Kafka の使い方

### 4.1 使いどころ

`APP_BROKER=kafka` のとき、Kafka は**イベントバス**として 2 種類のメッセージを運びます。

1. **書き込みコマンド**（`WriteRequested`）：エンドポイントは発行するだけで、コンシューマが実行します（4.5 参照）。
2. **ドメインイベント**（`EntityCreated`、`UserRegistered`、`RolePermissionsChanged` など）：トランザクションのコミット後に発行され、コンシューマが監査ログを書き、キャッシュを破棄します。

開発とテストには `APP_BROKER=memory`（プロセス内。書き込みリクエストは `publish` の中で同期的に実行され、外部サービスは不要）を使えます。小規模な構成では既定の Redis Streams で足ります（第 5 章）。

### 4.2 トピック設計

業務ドメインごとに 5 つのトピックを使い、書き込みコマンドとそれが引き起こすドメインイベントは同じトピックに流れます。

| トピック（既定のプレフィックス `hiaok`） | エンティティ | デッドレタートピック |
|---|---|---|
| `hiaok.organization` | 組織、テナント、プロジェクト | `hiaok.organization.dlq` |
| `hiaok.identity` | ユーザー、ユーザーグループ | `hiaok.identity.dlq` |
| `hiaok.authorization` | ロール、権限、メニュー | `hiaok.authorization.dlq` |
| `hiaok.hr` | 従業員、部門 | `hiaok.hr.dlq` |
| `hiaok.config` | システム設定 | `hiaok.config.dlq` |

- ルーティング表は `infrastructure/messaging/topics.py`（`Topic`、`TOPIC_OF_ENTITY`、`TOPIC_OF_EVENT`、`topic_of`）にあります。ルートの無い新しいエンティティやイベントは `UnroutableEvent` を送出し、テストも失敗します。
- **メッセージキー = 集約 ID**（書き込みコマンドでは対象の uuid）：同じ集約のメッセージは同じパーティションに入り、順序が保たれます。
- **ペイロード**：JSON `{"event_type": "...", "payload": {...}}`。ヘッダーに `event_type` が付きます。未知の `event_type`（新しいバージョンが出したイベント）はスキップします。

### 4.3 送信

プロデューサは `acks=all` と `enable_idempotence=True` で、`send_and_wait`（ブローカーが受け取ってから戻る）を使います。

```python
# エンドポイントに必要なのはこの 1 行だけ。残りはバスが行う
await submitter.update("Role", request.request_id, org_uuid, uuid, command)
#  → WriteRequested(entity_type="Role", command_type="Role.update", target_uuid=uuid, payload=...)
#  → topic_of(event) = hiaok.authorization、key = uuid
```

### 4.4 受信

トピックごとに 1 つのコンシューマ、グループ = `<KAFKA_GROUP_ID>.<topic>`（例：`hiaok.authorization`）、`auto_offset_reset=earliest`、**オフセットは手動コミット**です。

```
取得 → デシリアライズ → 購読者を探す → 実行（失敗したら 3 回リトライ、間隔 0.2 秒 / 0.4 秒 / 0.6 秒）
   ├─ 成功（または未知のイベント）→ オフセットをコミット
   └─ なお失敗（またはデコード不能）→ そのまま <topic>.dlq へコピー（ヘッダー source_topic / source_partition / source_offset を付与）→ オフセットをコミット
```

オフセットは処理成功かデッドレター送りの後にだけコミットされるため、メッセージは失われず、1 件の不良メッセージがトピック全体を止めることもありません。配信は**少なくとも 1 回**なので、コンシューマは冪等でなければなりません（書き込みコマンドは `requestId` から導出した結果レコードで重複を排除します。4.5 参照）。

ドメインイベントのコンシューマ（`application/usecase/event_handler.py`）：

| イベント | 処理 |
|---|---|
| すべてのドメインイベント（`WriteRequested` を除く） | `sys_log` に監査行を書く。`log_uuid` は `event_id` から導出するので再生しても安全 |
| `SysConfigChanged` | 設定キャッシュを破棄 |
| ユーザー・ユーザーグループ・ロール・権限の作成 / 更新 / 削除、ロールへの権限付与、メニュー割り当て、ユーザーへのロール割り当て | その組織の権限キャッシュを無効化 |

### 4.5 非同期書き込みの全体フロー

`add / update / delete` と専用の書き込みアクション（権限付与、移動、入社 / 退職 / 異動など）は、直接 DB に書きません。

```
POST /v1/api/hiaok/role/update          {requestId, reqInfo}
  endpoint:  WriteSubmitter.update("Role", ...) → WriteRequested を発行（key = 対象 uuid）→ すぐに返す
             {"code": 0, "resultInfo": {"requestId": "...", "uuid": "...", "status": "accepted"}}
  consumer:  handle_write → handlers["Role.update"] → 元のユースケース → service(@master) → DB
             成功：同じトランザクションで結果レコードを書く（sys_log、log_type=command）
             業務上の失敗（コード重複、ロールが無い など）：ロールバックして失敗を記録し、リトライしない
             例外（DB 停止 など）：再送出し、バスが 3 回リトライしてもだめならデッドレターへ
  結果の照会: POST /v1/api/hiaok/log/get-by-request  {orgUuid, targetRequestId}
             → status = success | failed | pending（code / msg / errorCode は同期呼び出しと同じ。msg は Accept-Language に従う）
```

- **新規作成時の uuid** は `requestId` から導出されます（`application/service/ids.py`）。そのためエンティティが作られる前にエンドポイントが uuid を返せます。コンシューマも同じ系列から ID を生成するので、再配信されても同じ ID になります。
- **冪等性**：結果レコードの `log_uuid` は `requestId` から導出され、既にあればそのメッセージはスキップされます。結果レコードと業務書き込みは同じトランザクションにあり、両方コミットされるか両方ロールバックされます。同じ `requestId` を再送しても 1 回しか実行されません。
- `pending` は、まだ消費されていない、リトライ中、またはデッドレター送り、のいずれかです。デッドレターになったコマンドは手作業での対応が必要です（4.7 参照）。
- **同期のままのエンドポイント**：ユーザー登録（`/user/add`）、パスワード変更、従業員の入社（`/employee/add`、アカウント付きも可）。平文パスワードを含むため、Kafka（メッセージが永続化される）には書けません。
- 書き込みエンドポイントを追加する = `build_write_handlers` にハンドラを登録する。

### 4.6 設定

| 環境変数 | 既定値 | 説明 |
|---|---|---|
| `APP_BROKER` | `redis` | `redis` \| `kafka` \| `memory` |
| `APP_CONSUME_EVENTS` | `true` | `false`：このプロセスは発行のみ。`hiaok worker` を別に起動して消費し、水平にスケールできる |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` | コンテナ内では `kafka:9092` |
| `KAFKA_TOPIC_PREFIX` | `hiaok` | トピック = `<prefix>.<domain>` |
| `KAFKA_GROUP_ID` | `hiaok` | コンシューマグループ = `<group_id>.<domain>` |
| `KAFKA_DLQ_SUFFIX` | `.dlq` | デッドレタートピックの接尾辞 |
| `KAFKA_CREATE_TOPICS` | `true` | 起動時に 10 トピック（業務 5 + デッドレター 5）を作成、既存なら無視。本番では無効にして運用側が作成することを推奨 |
| `KAFKA_NUM_PARTITIONS` | `3` | トピック作成時のパーティション数 |
| `KAFKA_REPLICATION_FACTOR` | `1` | トピック作成時のレプリカ数。本番ではブローカー数に合わせる |

デプロイ形態：

```
            ┌─ api（APP_CONSUME_EVENTS=false）──発行──▶ Kafka ◀──消費── worker × N（hiaok worker）
 クライアント ─┤
            └─ または単一プロセス：api が消費も行う（APP_CONSUME_EVENTS=true、既定）
```

同じグループの worker が多いほどパーティションが均等に分担されます。並列度の上限はパーティション数です。

### 4.7 運用

- **デッドレターの確認**：`hiaok.<domain>.dlq` を消費します。ヘッダー `source_topic / source_partition / source_offset` が元のメッセージを指します。本文は元と同じなので、原因を直してから元のトピックへ再発行してください（消費は冪等です）。
- **書き込みリクエストの結果確認**：`/log/get-by-request`。`pending` のときは、まずコンシューマのログ、次に対応する `.dlq` を確認します。
- **トピックの追加**：① `Topic` 列挙にメンバーを追加、② `TOPIC_OF_ENTITY` にエンティティを割り当て（ドメインイベントがあれば `TOPIC_OF_EVENT` にも）、③ 書き込みコマンドは `build_write_handlers` にハンドラを登録、④ `test_topics.py` にルーティングのケースを追加、⑤ 本番ではトピックと `.dlq` を先に作成。コンシューマとグループは列挙から自動生成されるので、バスのコードは変更不要です。
- ローカルで Kafka を試す：`docker compose --profile kafka up -d --build` で `APP_BROKER=kafka` を設定します。統合テストは Kafka に届かないとき自動的にスキップされます。

## 5. Redis の使い方

Redis には独立した 2 つの用途があり、別々のスイッチで切り替えます。

| 用途 | スイッチ | 説明 |
|---|---|---|
| イベントバス（Streams） | `APP_BROKER=redis`（既定） | Kafka との二者択一 |
| キャッシュ | `APP_CACHE=redis`（既定） | `APP_CACHE=memory` はプロセス内キャッシュ（単一ノード / テスト用。レプリカ間では共有されない） |

### 5.1 キャッシュ

すべてのキーに `REDIS_CACHE_PREFIX`（既定 `hiaok:`）が付き、既定の TTL は `REDIS_CACHE_TTL_SECONDS`（300 秒）です。インターフェースは `get / set(ttl) / delete` のみで、`hiaok_core.facade.Cache` が定義しています。

| キー（プレフィックスなし） | 内容 | TTL | 無効化 |
|---|---|---|---|
| `sys_config:<org>:<key>` | システム設定（リードスルー、`SysConfigService.get_by_key`） | 300 秒 | 書き込みのコミット後に `SysConfigChanged` イベントが破棄 |
| `session:<sha256(token)>` | ログインセッション `{userUuid, orgUuid, tenantUuid}` | `AUTH_SESSION_TTL_SECONDS`（2 時間） | ログアウトで削除、期限で自然に消える |
| `authz:<org>:<バージョン>:<user>` | ユーザーのロールコード + 権限コード | `AUTH_AUTHORITY_TTL_SECONDS`（60 秒） | 下記参照 |
| `authz_ver:<org>` | 組織の権限キャッシュのバージョン | 1 日 | 関連イベントの到着時に新しい値へ更新 |

**グループ全体の無効化**：キーに組織のバージョンが含まれます。ユーザー・ユーザーグループ・ロール・権限の変更イベントが届くと `authz_ver:<org>` だけを書き換えるので、その組織の全ユーザーの古いキーは即座に見つからなくなります（自然に期限切れになります）。走査して削除する必要はありません。

### 5.2 イベントバス（Redis Streams）

`APP_BROKER=redis` のときの `infrastructure/messaging/redis_stream.py`：

| 項目 | 実装 |
|---|---|
| 発行 | `XADD hiaok-events * data <json>`、`MAXLEN ~ 100000`（近似トリミング） |
| 消費 | コンシューマグループ `hiaok`、コンシューマ `consumer-1`、`XREADGROUP ... >` で 1 回に最大 50 件、1 秒ブロック |
| グループ作成 | 起動時に `XGROUP CREATE ... $ MKSTREAM`、既存なら無視。**グループ作成後の新しいメッセージだけを消費** |
| 確認応答 | 成功（または未知のイベント）の後にだけ `XACK` |
| リトライ | プロセス内で 3 回（0.2 秒 / 0.4 秒 / 0.6 秒） |
| 失敗 | `XACK` せず、メッセージは PEL（保留エントリ一覧）に残る |

Kafka との違い（選ぶときに知っておくべき点）：

- **ストリームは 1 本、コンシューマグループも 1 つ**で、ドメインごとには分かれず、**デッドレターキューもありません**。失敗したメッセージは PEL に残ります。`XPENDING hiaok-events hiaok` で確認し、`XAUTOCLAIM` で再取得するか、手作業で移します。
- グループ内に複数のコンシューマがいると、メッセージは分担されます。コンシューマ名は既定で固定の `consumer-1` なので、worker のレプリカを複数動かすときはレプリカごとに別の `REDIS_CONSUMER_NAME` を設定してください。
- キーによるパーティション分割がないため、複数のコンシューマが並列に動くと**集約ごとの順序は保証されません**。厳密な順序、高いスループット、長い保持期間が必要なら Kafka を選びます。
- 書き込みコマンドのフロー、冪等性、結果の照会は Kafka とまったく同じです。

### 5.3 設定

| 環境変数 | 既定値 | 説明 |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | キャッシュと Streams で共用 |
| `REDIS_STREAM` | `hiaok-events` | ストリーム名 |
| `REDIS_CONSUMER_GROUP` | `hiaok` | コンシューマグループ |
| `REDIS_CONSUMER_NAME` | `consumer-1` | レプリカごとに別の値を設定 |
| `REDIS_STREAM_MAXLEN` | `100000` | おおよその最大長 |
| `REDIS_CACHE_PREFIX` | `hiaok:` | キャッシュキーのプレフィックス（ストリームには付かない） |
| `REDIS_CACHE_TTL_SECONDS` | `300` | キャッシュの既定 TTL |

## 6. 国際化（i18n）

エラーメッセージは呼び出し元の言語で返ります。`Accept-Language: zh-CN,zh;q=0.9,en;q=0.8` → `q` が最大でサポートされている言語（`en` / `zh` / `ja`）を選び、レスポンスに `Content-Language` が付きます。どれもサポート外なら `APP_DEFAULT_LOCALE`（既定 `en`）を使います。

- **コードは変わりません**：`code` と `errorCode` は常に同じで、翻訳されるのは `msg` だけです。クライアントは `errorCode` で分岐し、`msg` は表示専用にしてください。
- **仕組み**：業務エラーは、カタログの英語テンプレートとパラメータから作られる値です。表示時に、メッセージを元のエラー仕様へ照合し（コードとテキストの両方が一致する必要があります）、パラメータを取り出して、`presentation/messages.py` の翻訳済みテンプレートに埋め込みます。`entity`（`User` → `ユーザー`）などの語も翻訳されます。翻訳の無いメッセージは英語のままです。
- **エラーメッセージの追加**：カタログで宣言した後、`presentation/messages.py` の `TEMPLATES` に `zh` と `ja` のエントリを追加します（キーは英語テンプレート）。`tests/unit/presentation/test_i18n.py` は、翻訳の欠落、プレースホルダーの不一致、対応するメッセージが存在しなくなった翻訳で失敗します。
- **言語の追加**：`LOCALES` にコードを追加し、`messages.py` の各エントリに言語を足します。足りない項目はテストが列挙します。
- **対象範囲**：API レスポンスの `msg`（非同期書き込みの失敗結果を含む）と、401 / 500 の固定文言。リクエストボディの形式エラーは pydantic 由来で翻訳されません。Swagger の説明文は中国語のままです。

## 7. API の規約

すべてのエンドポイントは `POST /v1/api/hiaok/<リソース>/<アクション>`、リクエストは `{requestId, reqInfo}`、レスポンスは `{code, msg, resultInfo}` で、フィールドは camelCase です。組織は `reqInfo.orgUuid`、対象リソースは `reqInfo.uuid` です。

| ヘッダー | 説明 |
|---|---|
| `Authorization: Bearer <token>` | 保護されたエンドポイントで必須（`POST /auth/login` で取得） |
| `Accept-Language` | `en` / `zh` / `ja`、`msg` の言語 |
| `X-Request-Id` | トレース ID。レスポンスヘッダーにそのまま返る。省略時は自動生成 |
| `X-Operator` | `AUTH_ENABLED=false` のときだけ使用 |

想定内のエラーは HTTP 200 と `code` で表します。

| code | 意味 |
|---|---|
| 0 | 成功 |
| 400 | 業務検証の失敗、またはリクエストボディの形式エラー（`errorCode` = `invalid_request`） |
| 401 | 未ログイン / トークン無効（`unauthenticated`）、またはユーザー名・パスワードの誤り（`invalid_credentials`） |
| 403 | 権限なし（`permission_denied` / `role_denied`）、または他組織の操作（`org_mismatch`） |
| 404 | リソースが存在しない |
| 409 | 状態の競合（コード重複、システムロールの削除 など） |
| 502 / 500 | 上流サービスの失敗 / 想定外のシステムエラー（この 2 つは実際の HTTP ステータス。詳細はログにのみ出力） |

一覧系は `reqInfo` で `offset`（既定 0）と `limit`（既定 20、最大 200）を渡し、`resultInfo` は `items / total / offset / limit` です。

Swagger：`http://localhost:8000/docs` · ReDoc `/redoc` · `/openapi.json`。保護されたエンドポイントには Bearer スキームが宣言されており、右上の Authorize にトークンを入力すれば試せます。ドキュメントを公開したくない場合は `APP_DOCS_ENABLED=false` を設定します。

## 8. 設定リファレンス

`APP_ENV` でプロファイルを選びます（`dev`：Redis + マスター 5432 / スレーブ 5433、`test`：メモリ + 単一 DB、`docker`：compose 内のマスター・スレーブ）。

| プレフィックス | 変数 | 既定値 |
|---|---|---|
| `APP_` | `NAME` `ENV` `HOST` `PORT` `LOG_LEVEL` | `hiaok` / `dev` / `0.0.0.0` / `8000` / `INFO` |
| | `BROKER` | `redis`（`kafka` \| `memory`） |
| | `CACHE` | `redis`（`memory`） |
| | `CONSUME_EVENTS` | `true` |
| | `DOCS_ENABLED` | `true` |
| | `DEFAULT_LOCALE` | `en`（`zh` \| `ja`） |
| `AUTH_` | `ENABLED` | `true` |
| | `SESSION_TTL_SECONDS` | `7200` |
| | `AUTHORITY_TTL_SECONDS` | `60`（1〜86400） |
| | `PLATFORM_ORG_UUID` | 空 |
| `DB_` | `MASTER_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/hiaok` |
| | `SLAVE_URL` | 空（読み取りもマスターへ） |
| | `POOL_SIZE` `MAX_OVERFLOW` `POOL_RECYCLE` `ECHO` | `10` / `20` / `1800` / `false` |
| `REDIS_` / `KAFKA_` | 第 4・5 章を参照 | |

## 9. テストと注意事項

```bash
uv run pytest                          # すべて（サービスが起動していなければ統合テストは自動でスキップ）
uv run pytest -m "not integration"
docker compose up -d redis && uv run pytest -m integration
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

```text
tests/
├─ unit/domain/          # 値オブジェクト、集約、ツリー、認可ルール
├─ unit/application/     # 書き込みコマンド（冪等性、失敗の記録）、イベント処理
├─ unit/infrastructure/  # serde、インメモリバス、トピックのルーティング、キャッシュ、DAO 変換
├─ unit/presentation/    # エンベロープ、例外のマッピング、認可ガード、i18n、OpenAPI
├─ unit/test_architecture.py    # レイヤーと命名のルール
└─ integration/          # 実際の Redis / Kafka が必要。届かなければ自動でスキップ
```

- `user` は PostgreSQL の予約語です。ORM は自動で引用符を付けますが、手書き SQL では `"user"` と書く必要があります。
- スレーブにはレプリケーション遅延があります。書き込み直後の読み取りでは、一時的に見えないことがあります。非同期書き込みでは、すぐ読み戻すのではなく `/log/get-by-request` で結果を確認してください。
- イベントはコミット後に発行されるため、その間にプロセスが落ちるとイベントが失われます。厳密な保証が必要なら transactional outbox に切り替えてください。
- デッドレターになった書き込みコマンドは `pending` のまま残り、手作業での対応が必要です。

## ライセンス

[MIT](LICENSE) © 2026 PAN JIE <sanbaikuai@gmail.com>
