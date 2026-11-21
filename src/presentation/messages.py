"""Translations of the business error messages.

Keyed by the *English template* of the error spec (``ErrorSpec.template``, or the generic ``not_found`` message) so
two specs that share a code (``invalid_parent``) can still read differently. ``{placeholders}`` are filled with the
parameters of the error. English is the source text and needs no entry. A missing entry falls back to English;
``tests/unit/presentation/test_i18n.py`` fails when a catalog spec has no translation.
"""

from __future__ import annotations

type Translations = dict[str, dict[str, str]]

NOT_FOUND = "{entity} '{id}' not found"  # hiaok_core.exception.not_found: generic, not part of any catalog

TEMPLATES: Translations = {
    NOT_FOUND: {"zh": "{entity} '{id}' 不存在", "ja": "{entity} '{id}' が見つかりません"},
    # usecase
    "roles {roles} belong to another tenant": {
        "zh": "角色 {roles} 属于其他租户",
        "ja": "ロール {roles} は別のテナントに属しています",
    },
    "user '{user_uuid}' is disabled": {
        "zh": "用户 '{user_uuid}' 已被禁用",
        "ja": "ユーザー '{user_uuid}' は無効化されています",
    },
    "employee '{employee_uuid}' is not active": {
        "zh": "员工 '{employee_uuid}' 不在职",
        "ja": "従業員 '{employee_uuid}' は在籍していません",
    },
    "tenant_uuid is required to open a login account": {
        "zh": "开通登录账号必须提供 tenant_uuid",
        "ja": "ログインアカウントの開設には tenant_uuid が必要です",
    },
    "{command_type}: {problem}": {"zh": "{command_type}：{problem}", "ja": "{command_type}：{problem}"},
    "no handler for {command_type}": {
        "zh": "没有处理 {command_type} 的处理器",
        "ja": "{command_type} のハンドラがありません",
    },
    "invalid username or password": {"zh": "用户名或密码错误", "ja": "ユーザー名またはパスワードが正しくありません"},
    "captcha is missing, expired or wrong": {
        "zh": "验证码缺失、已过期或错误",
        "ja": "認証コードがないか、期限切れか、正しくありません",
    },
    # infrastructure
    "{what} already exists ({constraint})": {
        "zh": "{what} 已存在（{constraint}）",
        "ja": "{what} は既に存在します（{constraint}）",
    },
    # value objects
    "password {reason}": {"zh": "密码{reason}", "ja": "パスワードは{reason}"},
    "{field} is required": {"zh": "{field} 不能为空", "ja": "{field} は必須です"},
    "{field} must be <= {max_len} chars": {
        "zh": "{field} 长度不能超过 {max_len} 个字符",
        "ja": "{field} は {max_len} 文字以内で入力してください",
    },
    "{field} must match {pattern}": {
        "zh": "{field} 必须匹配 {pattern}",
        "ja": "{field} は {pattern} に一致する必要があります",
    },
    "username must be 3-64 chars of [A-Za-z0-9_.@-]": {
        "zh": "用户名必须是 3-64 位，仅含字母、数字和 _ . @ -",
        "ja": "ユーザー名は 3〜64 文字の英数字と _ . @ - のみ使用できます",
    },
    "invalid email address": {"zh": "邮箱格式不正确", "ja": "メールアドレスの形式が正しくありません"},
    "invalid phone number": {"zh": "手机号格式不正确", "ja": "電話番号の形式が正しくありません"},
    # entities
    "a group cannot be its own parent": {
        "zh": "用户组不能以自己为父级",
        "ja": "ユーザーグループは自分自身を親にできません",
    },
    "a menu cannot be its own parent": {"zh": "菜单不能以自己为父级", "ja": "メニューは自分自身を親にできません"},
    "a department cannot be its own parent": {"zh": "部门不能以自己为父级", "ja": "部門は自分自身を親にできません"},
    "unknown value_type '{value_type}'": {
        "zh": "未知的 value_type '{value_type}'",
        "ja": "不明な value_type '{value_type}' です",
    },
    "'{value}' is not a valid {value_type}": {
        "zh": "'{value}' 不是合法的 {value_type}",
        "ja": "'{value}' は有効な {value_type} ではありません",
    },
    "tenant '{tenant_uuid}' is disabled or expired": {
        "zh": "租户 '{tenant_uuid}' 已禁用或已过期",
        "ja": "テナント '{tenant_uuid}' は無効または期限切れです",
    },
    "system role '{code}' cannot be deleted": {
        "zh": "系统角色 '{code}' 不能删除",
        "ja": "システムロール '{code}' は削除できません",
    },
    "cannot transfer an employee who has left": {
        "zh": "已离职的员工不能调动",
        "ja": "退職済みの従業員は異動できません",
    },
    "employee is already linked to user '{user_uuid}'": {
        "zh": "员工已关联用户 '{user_uuid}'",
        "ja": "従業員は既にユーザー '{user_uuid}' に紐付いています",
    },
    "leave_date must be after hire_date": {
        "zh": "离职日期必须晚于入职日期",
        "ja": "退職日は入社日より後でなければなりません",
    },
    "parent '{parent}' not found": {"zh": "父节点 '{parent}' 不存在", "ja": "親ノード '{parent}' が見つかりません"},
    "the new parent is inside the node's own subtree": {
        "zh": "新的父节点位于该节点自己的子树内",
        "ja": "新しい親がこのノード自身の子孫にあります",
    },
    # security
    "requires permission {required}": {"zh": "需要权限 {required}", "ja": "権限 {required} が必要です"},
    "requires role {required}": {"zh": "需要角色 {required}", "ja": "ロール {required} が必要です"},
    "not allowed to act on organization '{org_uuid}'": {
        "zh": "无权操作组织 '{org_uuid}'",
        "ja": "組織 '{org_uuid}' を操作する権限がありません",
    },
}

# fixed messages that are not produced by a spec
STATIC: Translations = {
    "authentication required": {"zh": "需要登录", "ja": "認証が必要です"},
    "internal error": {"zh": "系统内部错误", "ja": "内部エラーが発生しました"},
}

# parameter values that are words rather than data: translated before they are put into a message
ENTITY_NAMES: Translations = {
    "Organization": {"zh": "组织", "ja": "組織"},
    "Tenant": {"zh": "租户", "ja": "テナント"},
    "User": {"zh": "用户", "ja": "ユーザー"},
    "UserGroup": {"zh": "用户组", "ja": "ユーザーグループ"},
    "Project": {"zh": "项目", "ja": "プロジェクト"},
    "Role": {"zh": "角色", "ja": "ロール"},
    "Permission": {"zh": "权限", "ja": "権限"},
    "Menu": {"zh": "菜单", "ja": "メニュー"},
    "Department": {"zh": "部门", "ja": "部門"},
    "Employee": {"zh": "员工", "ja": "従業員"},
    "SysConfig": {"zh": "系统配置", "ja": "システム設定"},
}
PASSWORD_REASONS: Translations = {
    "must be at least 8 chars": {"zh": "长度不能少于 8 位", "ja": "8文字以上である必要があります"},
    "must mix letters and digits/symbols": {
        "zh": "必须同时包含字母和数字/符号",
        "ja": "英字と数字・記号を組み合わせる必要があります",
    },
}
PARAM_WORDS: dict[str, Translations] = {"entity": ENTITY_NAMES, "reason": PASSWORD_REASONS}
