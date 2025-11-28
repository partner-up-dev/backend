## **1. Configuration Files**

| File | Description |
|------|-------------|
| .env (lines 40-44) | `SUPABASE_URL`, `SUPABASE_SERV_KEY`, `SUPABASE_ANON_KEY` environment variables |
| .env.example (lines 40-44) | Same env vars template |
| settings.py (lines 32-35) | Settings model: `supabase_url`, `supabase_serv_key`, `supabase_anon_key` |
| supabase | 3 JSON config files: `supabase.base.json`, `supabase.development.json`, `supabase.production.json` |
| pyproject.toml (line 28) | Package dependency: `"supabase-auth>=2.12.0,<3.0.0"` |

---

## **2. Source Code Files**

### **Account Service**
| File | Supabase Usage |
|------|----------------|
| account.py | `SupabaseAuth` class using Supabase Auth API |
| wxmp.py | Imports & uses `SupabaseAuth` |
| __init__.py | Exports `SupabaseAuth` |

### **Main Service**
| File | Supabase Usage |
|------|----------------|
| main.py | `from dal import SupabaseAnonPostgrest`, `dal=SupabaseAnonPostgrest` |
| contribution.py | `from dal import SupabaseAnonPostgrest`, `dal=SupabaseAnonPostgrest` |
| merge.py | `from dal import SupabaseAnonPostgrest`, `dal=SupabaseAnonPostgrest` |
| main.py | `SupabaseUser.from_id()` usage |
| clause.py | `from app.libs.postgresql import supabase_serv_db` - fetch/insert |
| contract.py | `from app.libs.postgresql import supabase_serv_db` - fetch/insert/update |
| commute.py | `supabase_serv_db.update()` |
| ride_hailing.py | `supabase_serv_db.update()` |

### **Ride Hailing Service**
| File | Supabase Usage |
|------|----------------|
| __init__.py | Multiple imports: `from supabase import Client`, `supabase_serv`, `get_supabase_db`, `SupabaseIdentityProvider` |
| tasks.py | `from backend_common.libs.database import supabase_serv_db` - fetch operations |
| __init__.py | `from backend_common.libs.database import supabase_serv_db` - fetch |
| __init__.py | `from backend_common.libs.database import supabase_serv_db` - fetch |

### **Communication Service**
| File | Supabase Usage |
|------|----------------|
| channel_weixin.py | `from dal import SupabaseServPostgrest` - select operations |

### **Libraries**
| File | Supabase Usage |
|------|----------------|
| oss.py | `SupabaseStorage` class for file storage (upload/download/delete) |
| ca.py | `from app.libs.postgresql import supabase_serv_db` - fetch/upsert/update |
| pdf.py | Uses `supabase_serv_storage` from oss.py for PDF storage |

### **Tests**
| File | Supabase Usage |
|------|----------------|
| test_trip_pr.py | `from interface_main.dal import SupabaseServPostgrest` |

---

## **3. Documentation**
| File | Supabase Mentions |
|------|-------------------|
| README.md (lines 13, 31, 51-57) | Dependencies mention, setup instructions |

---

## **4. External Package Dependencies** (from imports)

These are imported from external packages that need to be replaced:
- `supabase` (native SDK)
- `supabase-auth` (auth SDK)  
- `dal` module: `SupabaseAnonPostgrest`, `SupabaseServPostgrest`
- `backend_common.libs.supabase`: `supabase_serv`
- `backend_common.libs.database`: `supabase_serv_db`
- `backend_common.utils.manager`: `get_supabase_db`
- `interface_common.authenticate`: `SupabaseIdentityProvider`
- `interface_main.dal`: `SupabaseServPostgrest`
- `app.libs.postgresql`: `supabase_serv_db`
- `app.libs.supabase`: `supabase_serv`