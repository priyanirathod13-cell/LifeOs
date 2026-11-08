# LifeOS — Database Architecture & Schema Documentation

## 1. Current Database Status (Step 01, Step 02 & Step 03)

- **Database Engine**: MySQL 10.4.32 / 8.0+
- **Database Name**: `lifeos_db`
- **Default Character Set**: `utf8mb4`
- **Default Collation**: `utf8mb4_unicode_ci`
- **ORM**: Django ORM (`django.db.backends.mysql` via `mysqlclient`)
- **Active Migrations**:
  - `accounts.0001_initial`: Initial User model creation.
  - `accounts.0002_user_bio_user_timezone_pref_alter_user_email`: Added unique email constraint, bio, and timezone preference fields.

---

## 2. Active Implemented Tables

The following tables exist in `lifeos_db` as verified by database migrations:

### `accounts_user` (Custom User Model)
Defined in `apps.accounts.models.User` inheriting from `django.contrib.auth.models.AbstractUser`.
Configured via `AUTH_USER_MODEL = 'accounts.User'`.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `BIGINT` | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for user |
| `password` | `VARCHAR(128)` | NOT NULL | PBKDF2/SHA256 hashed password string |
| `last_login` | `DATETIME(6)` | NULLABLE | Timestamp of last user authentication |
| `is_superuser` | `TINYINT(1)` | NOT NULL, DEFAULT 0 | Grants all admin permissions |
| `username` | `VARCHAR(150)` | UNIQUE, NOT NULL | Unique username handle |
| `first_name` | `VARCHAR(150)` | NOT NULL | User first name |
| `last_name` | `VARCHAR(150)` | NOT NULL | User last name |
| `email` | `VARCHAR(254)` | UNIQUE, NOT NULL | Unique primary email credential |
| `is_staff` | `TINYINT(1)` | NOT NULL, DEFAULT 0 | Admin site login permission |
| `is_active` | `TINYINT(1)` | NOT NULL, DEFAULT 1 | Active account status flag |
| `date_joined` | `DATETIME(6)` | NOT NULL | Account registration timestamp |
| `created_at` | `DATETIME(6)` | NOT NULL, auto_now_add | LifeOS record creation timestamp |
| `updated_at` | `DATETIME(6)` | NOT NULL, auto_now | LifeOS record update timestamp |
| `bio` | `LONGTEXT` | NOT NULL, DEFAULT '' | Personal behavioral philosophy and vision |
| `timezone_pref` | `VARCHAR(50)` | NOT NULL, DEFAULT 'Asia/Kolkata' | User primary timezone preference |

### Supporting Django Auth & Session Tables
- `accounts_user_groups`: Many-to-many relationship linking users to permissions groups.
- `accounts_user_user_permissions`: Direct user-to-permission grants.
- `auth_group`: Role/group definitions.
- `auth_group_permissions`: Role-to-permission mapping.
- `auth_permission`: Individual system permission records.
- `django_content_type`: System content type tracking.
- `django_migrations`: Track applied migration operations.
- `django_session`: User session storage.
- `django_admin_log`: Audit trail for actions taken inside `/admin/`.

---

## 3. Schema Roadmap (Upcoming Steps)

*Note: In accordance with Step 01, 02, and 03 architectural rules, no domain models have been created prematurely:*

1. **Step 04**: Tasks, Habits, Timetable slots, Routines, and Study subjects (all with foreign keys to `settings.AUTH_USER_MODEL`).
2. **Step 05**: Daily check-in logs, biometric states, and journal entries.
3. **Step 06**: Decisions, Expected Payoffs, Mistakes, and Lessons Learned.
4. **Step 07**: Analytics aggregations and behavioral correlation records.
