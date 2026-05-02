# Phantasm 軍・政府諜報機関レベルへの硬化ロードマップ

**最終更新**: 2026-05-02  
**ステータス**: 戦略提案フェーズ

---

## 概要

本ドキュメントは、Phantasmを軍・政府諜報機関の運用基準に耐えうるツールへ引き上げるための包括的な改善戦略を定義します。「ローコストで守る」という設計思想を維持しつつ、暗号基盤、鍵管理、メモリ安全性、監査、認証、強要対策、サプライチェーン、ソフトウェア品質などの領域ごとに改善目標を明確化します。

---

## 改善戦略（10領域）

### 1. 暗号基盤の規格適合

**現状の問題**
- AES-GCM + Argon2idは技術的に妥当だが、規格準拠を主張していない
- 政府・軍の調達基準（FIPS, CNSA等）を満たさない

**改善目標**

#### FIPS 140-3 Level 1 準拠の暗号モジュール化
- NIST承認アルゴリズムのみの使用
- Power-on Self Test（自己テスト機構）の実装
- 鍵のゼロ化手順の形式化
- 承認済みRNG（DRBG）の統合

**現在の採用**: Python `cryptography` の `os.urandom()` 依存  
**改善案**: 
```
NIST SP 800-90A準拠のDRBG + エントロピー品質検証
```

#### KDF のNIST準拠化
- **現状**: Argon2id（NIST非承認）
- **改善案**: 
  - `HKDF-SHA-256` への移行、または
  - `Argon2id` を前処理、その出力を `HKDF-SHA-256` に通す二段構成

#### NSA CSfC Data-at-Rest（DAR）への対応
- **要件**: 2層の独立した暗号化
- **現状**: 単層のAES-GCM暗号化
- **改善案**:
  - 外層: OS/ファイルシステムレベル（dm-crypt/LUKS）
  - 内層: Phantasm アプリケーション層暗号化

#### CNSA 2.0 への移行準備
- AES-256 は維持
- ハッシュをSHA-384以上に
- ポスト量子暗号（CRYSTALS-Kyber等）への対応パス設計

**実装優先度**: 高  
**関連Issue**: `[FEAT] FIPS 140-3 Level 1 準拠の暗号モジュール設計`

---

### 2. 鍵管理の厳格化

**現状の問題**
- 鍵素材（`access.bin`、`lock.bin`）がファイルシステム上に平文または簡易暗号化で存在
- ライフサイクル管理が未定義

**改善目標**

#### Sensitive Security Parameter（SSP）管理体系の確立

**鍵生成**
```python
# 現状
key = os.urandom(32)

# 改善: NIST SP 800-90A準拠DRBG + エントロピー検証
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends.openssl.backend import backend as default_backend

# 推奨実装: CTR_DRBG or Hash_DRBG
```

**鍵保存**
- メモリ上の鍵は使用後即座にゼロ化
- Python GC に依存しない明示的なメモリワイプ（`mlock` + 手動ゼロフィル）

**鍵破棄**
- `brick` コマンドのゼロ化範囲を厳密に定義
- ゼロ化対象バイト範囲・回数・検証手順を仕様化

#### PKCS#11 インターフェース対応
- `PHANTASM_HARDWARE_SECRET_FILE` を拡張
- YubiKey、スマートカード等のローコストHSM対応
- 鍵素材がファイルシステムに書き込まれない運用を実現

**実装優先度**: 高  
**関連Issue**: `[FEAT] PKCS#11対応の外部トークン鍵注入`, `[FEAT] SSP管理体系の形式化`

---

### 3. メモリ安全性とサイドチャネル対策

**現状の問題**
- Python実装のため、メモリ上の秘密データの制御がランタイム任せ
- コールドブート攻撃、メモリダンプ、サイドチャネルが現実的脅威

**改善目標**

#### 暗号コアのネイティブ実装への分離

**構成**
```
┌─ Phantasm (Python)
│  └─ FFI/ctypes
│      └─ cryptasm_core (C/Rust)
│         ├─ AES-GCM (constant-time)
│         ├─ KDF (constant-time)
│         ├─ mlock() / explicit_bzero()
│         └─ エントロピー供給
```

**実装内容**
- `mlock()` で暗号鍵を含むメモリページをスワップ禁止
- `explicit_bzero()` / `SecureZeroMemory()` で確実なゼロ化
- 定数時間比較を全認証処理に適用
- データ依存分岐の排除

#### コアダンプ・スワップの抑止

```python
# 起動シーケンスに追加
import prctl

def harden_memory_safety():
    # コアダンプ禁止
    prctl.set_prctl(prctl.PR_SET_DUMPABLE, 0)
    
    # 全メモリページのスワップアウト禁止
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_MEMLOCK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        os.mlockall(os.MCL_CURRENT | os.MCL_FUTURE)
    except (OSError, PermissionError):
        logger.warning("mlockall failed; running without swap protection")
```

**実装優先度**: 高（工数は大きいが効果大）  
**関連Issue**: `[FEAT] 暗号コアのRust/C実装への分離`, `[FEAT] メモリ保護機構の実装`

---

### 4. 監査ログとフォレンジック対応

**現状の問題**
- `events.log` がオプション機能で、ログの完全性保証がない
- 改ざん・削除の検知不可

**改善目標**

#### 改ざん検知付き監査ログの実装

**ハッシュチェーン方式**
```json
{
  "sequence": 1,
  "timestamp": "2026-05-02T10:30:00Z",
  "event": "ui_face_lock_enrolled",
  "source": "web",
  "previous_hash": "sha256:abc123...",
  "entry_hash": "sha256:def456...",
  "hmac_sha256": "signature..."
}
```

**特性**
- 前エントリのハッシュを次エントリに含める
- HMAC で整合性を二重保証
- 改ざん・削除の即座の検知が可能

**記録対象**
- 暗号操作の成功/失敗
- 鍵アクセス（読み込み、破棄）
- 制限付きアクション実行
- 認証試行（成功/失敗/回数）
- 秘密情報は含まない形式で記録

#### 監査ポリシーの強制化

```yaml
# 新設定: audit_profile
PHANTASM_AUDIT_PROFILE: "government"  # "disabled" | "standard" | "government"
PHANTASM_AUDIT_EXPORT_INTERVAL: 3600  # 秒（自動エクスポート間隔）
PHANTASM_AUDIT_EXPORT_TARGET: "/mnt/external-audit"  # ローカルUSBストレージ等
```

**実装優先度**: 最高（低コスト・高効果）  
**関連Issue**: `[FEAT] ハッシュチェーン付き監査ログ`, `[FEAT] 監査ポリシー強制化`

---

### 5. 認証の強化と暗号的強度の明確化

**現状の問題**
- ORB物体マッチングは高エントロピー認証ではない
- 顔認証はUI専用、認証階層が未整理
- 認証試行数制限がない

**改善目標**

#### 認証階層の再設計

```
┌─ レベル1（必須）: 強パスワード/パスフレーズ
│  └─ Argon2id/NIST KDF → 暗号鍵導出
│     （暗号的強度：ここで確定）
│
├─ レベル2（推奨）: 外部トークン（PKCS#11）
│  └─ 鍵素材注入
│     （多要素認証、鍵管理の分離）
│
└─ レベル3（運用補助）: 物体マッチング/顔認証
   └─ アクセスキュー（暗号強度には寄与しない）
      （実装障壁の追加、検出困難性向上）
```

#### パスワード・パスフレーズポリシーの強制

```python
# 新設定: password_policy
PHANTASM_PASSWORD_MIN_ENTROPY: 80  # bits (NIST SP 800-63B基準)
PHANTASM_PASSWORD_DICTIONARY_CHECK: True  # 辞書チェック有効
PHANTASM_PASSPHRASE_MODE: "diceware"  # "standard" | "diceware"
```

#### 認証試行回数の制限と指数的遅延

```python
class AuthenticationLimiter:
    """
    レート制限 + 指数的バックオフ
    試行回数: 5回失敗で60秒ロック → 次5回で600秒 → ...
    """
    def check_attempt(self, client_id):
        failures = self.get_failures(client_id)
        if failures >= 5:
            lockout_duration = 60 * (2 ** (failures // 5))
            if self.is_locked(client_id, lockout_duration):
                raise AuthenticationLockedError(lockout_duration)
```

**実装優先度**: 高  
**関連Issue**: `[FEAT] 認証階層の形式化`, `[FEAT] パスフレーズポリシー強制`, `[FEAT] 指数的バックオフの実装`

---

### 6. 強要対策（Duress/Coercion）の観測不可分性

**現状の問題**
- `PHANTASM_DURESS_MODE` やパニックトリガーの仕様が曖昧
- 攻撃者からの観測可能性が未分析

**改善目標**

#### 観測不可分性の設計目標化

**分析対象**
- 処理時間の差異 → タイミング攻撃
- ネットワーク挙動の差異 → トラフィック分析
- ディスクI/Oパターンの差異 → 物理メモリアクセス分析
- エラーメッセージの差異 → 状態推測

**対策**
```python
def access_vault_indistinguishable(password, mode="normal"):
    """
    Duress と通常アクセスのタイミング・応答を統一
    """
    start_time = time.time()
    target_duration = 2.5  # 秒
    
    try:
        if mode == "normal":
            result = vault.unlock(password)
        else:  # duress
            result = vault.unlock_duress(password)
    finally:
        # 処理時間を定数に近づけるパディング
        elapsed = time.time() - start_time
        if elapsed < target_duration:
            time.sleep(target_duration - elapsed)
    
    return result
```

#### Duress動作の仕様文書化

```yaml
# duress_spec.yaml
duress_behavior:
  access_success:
    - action: "unlock_slot_a"
      description: "スロットAのデータを開示"
    - action: "zero_slot_b_key"
      description: "スロットBの鍵素材をゼロ化"
    - action: "clear_sensitive_flags"
      description: "顔認証テンプレート等の削除"
    - action: "log_neutral_event"
      description: "ログに通常アクセスと区別不可能なイベント記録"
      
  transaction_atomicity: "全操作をアトミックに実行、途中失敗時のロールバック定義"
  timing_guarantee: "ターゲット時間内での完了保証（リトライなし）"
```

**実装優先度**: 中～高  
**関連Issue**: `[FEAT] Duress動作の観測不可分性分析と実装`

---

### 7. ソフトウェアサプライチェーンの保護

**現状の問題**
- `pip install -r requirements.txt` で外部依存を取得、完全性検証なし
- ソフトウェア供給チェーン攻撃への耐性がない

**改善目標**

#### 依存関係の固定と検証

```
# requirements.txt (現在)
cryptography==41.0.0

# 改善: --require-hashes 対応
# requirements-hashes.txt
cryptography==41.0.0 \
    --hash=sha256:abc123...
numpy==1.24.0 \
    --hash=sha256:def456...

# インストール
pip install -r requirements-hashes.txt --require-hashes
```

#### SBOM（Software Bill of Materials）の生成・署名

```bash
# CycloneDX形式での出力
pip install cyclonedx-bom
cyclonedx-py -o sbom.xml -f xml

# SPDX形式での出力
spdx-sbom-generator --output-file sbom.spdx
```

**自動化**
```yaml
# .github/workflows/sbom.yml
- name: Generate SBOM
  run: cyclonedx-py -o dist/sbom.json -f json
  
- name: Sign SBOM
  run: gpg --armor --sign dist/sbom.json
```

#### ビルド再現性の確保

```bash
# Dockerfile 等でのマルチステージビルド
# 全依存をロック、同一出力の再現可能性を検証

# リリースとして署名
gpg --armor --sign phantasm-release-${VERSION}.tar.gz
```

**実装優先度**: 高  
**関連Issue**: `[FEAT] SBOM自動生成パイプライン`, `[FEAT] ビルド再現性の検証`, `[FEAT] GPG署名の統合`

---

### 8. WebUIの攻撃面削減

**現状の問題**
- WebUIはブラウザキャッシュ、履歴、CSRF、ローカルプロセス間通信など攻撃面を増加
- 軍用高セキュリティ環境には不適切な場合がある

**改善目標**

#### 軍用プロファイル: WebUI無効化オプション

```python
# config.py
def web_ui_enabled():
    profile = os.environ.get("PHANTASM_PROFILE", "default")
    return profile != "military-cli-only"

@app.get("/")
async def home(request: Request):
    if not web_ui_enabled():
        raise HTTPException(status_code=404)
    # ...
```

#### WebUI使用時の強制セキュリティヘッダ

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'none'; script-src 'self'; style-src 'self'"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

#### セッション・トークンの短寿命化と厳格クッキー設定

```python
# 現状: FACE_SESSION_COOKIE TTL 300秒
# 改善: 60秒に短縮、Secure; HttpOnly; SameSite=Strict を強制

response.set_cookie(
    FACE_SESSION_COOKIE,
    token,
    max_age=60,  # 60秒
    httponly=True,
    secure=True,
    samesite="strict",
    domain="localhost",  # localhost のみ
    path="/"
)
```

#### ランダムパスプレフィックスによる隠蔽

```python
# 起動時に生成
EMERGENCY_PREFIX = secrets.token_hex(8)  # e.g., "a7f2c3d9"

# ルート定義時に動的に変更
app.add_route(f"/{EMERGENCY_PREFIX}/emergency/brick", emergency_brick, methods=["POST"])

# ドキュメントには記載せず、初回セットアップ時に通知のみ
```

**実装優先度**: 中  
**関連Issue**: `[FEAT] WebUI無効化プロファイル`, `[FEAT] セキュリティヘッダの強化`, `[FEAT] セッションTTL短縮`

---

### 9. 安全削除の暗号的消去への転換

**現状の問題**
- SDカードのウェアレベリングのため、ファイル上書き削除が保証できない
- 物理的削除に頼っている

**改善目標**

#### 暗号的消去（Cryptographic Erase）の正式採用

**戦略転換**
```
従来: ファイルを複数回上書き → ウェアレベリングで効果不明 → 物理破壊依存

改善: 暗号鍵を確実に破壊 → 鍵なしではデータは無意味 → 物理メディア破棄不要
```

#### `brick` コマンドの再定義

```python
@cli.command("reset")
def reset_face_lock_and_vault():
    """
    暗号的消去: 全鍵素材をゼロ化、デバイスをアクセス不可能な状態へ
    
    消去対象:
      - access.bin (Vault KDF導出の根鍵)
      - lock.bin (顔認証テンプレート暗号化鍵)
      - face.bin (顔テンプレート本体)
      - state encryption key (全状態データ暗号化鍵)
    
    ゼロ化手順:
      1. メモリロード（mlock）
      2. 複数回ゼロフィル（NSA規格: 最低3回）
      3. 検証読み込み（ゼロ確認）
      4. ファイル削除（標準`unlink`）
    
    失敗時: ロック状態で保持、再試行を促す
    """
    ...
```

#### 揮発性メモリ優先オプション

```python
PHANTASM_VOLATILE_KEYS_ONLY=1  # 鍵素材を tmpfs/ramfs のみに保持
                               # 再起動時に自動消去
                               # 永続化は外部HSM必須
```

**実装優先度**: 最高  
**関連Issue**: `[FEAT] 暗号的消去の形式化`, `[FEAT] brick コマンドの仕様化`, `[FEAT] 揮発性メモリオプション`

---

### 10. 形式的検証と認証取得のロードマップ

**現状の問題**
- 脅威モデルが文章的、体系的分析がない
- 第三者検証がない

**改善目標**

#### 段階的な認証取得パス

| フェーズ | 目標 | 実施内容 | 期間 | コスト |
|---------|------|---------|------|--------|
| **Phase 1** | 内部品質基盤 | 静的解析（Bandit, Semgrep）、ファジング、UT網羅80%以上、脅威STRIDE分析 | 2-3ヶ月 | 低 |
| **Phase 2** | 独立セキュリティ監査 | 第三者によるソースコード監査、ペネテスト、結果公開 | 3ヶ月 | 中～高 |
| **Phase 3** | Common Criteria評価 | NIAP PP対応、EAL2+評価取得 | 6-12ヶ月 | 高 |
| **Phase 4** | FIPS 140-3 Level 1 | 暗号モジュールのCMVP認証 | 6ヶ月 | 高 |
| **Phase 5** | 運用認定 | 特定政府機関での認定試験・承認取得 | 3-6ヶ月 | 高 |

#### 脅威モデルの形式化

**STRIDE フレームワーク適用**
```
┌─ Spoofing (偽装)
│  └─ 弱点: 初回UI顔認証登録時の識別なし
│     └─ 対策: 出所明確化要件の追加
│
├─ Tampering (改ざん)
│  └─ 弱点: 監査ログの整合性保証なし
│     └─ 対策: ハッシュチェーン追加 [Phase 1対応]
│
├─ Repudiation (否認)
│  └─ 弱点: アクションのトレーサビリティが限定的
│     └─ 対策: 監査ポリシー強制化 [Phase 1対応]
│
├─ Information Disclosure (情報漏洩)
│  └─ 弱点: メモリダンプ時の秘密データ露出
│     └─ 対策: 暗号コア分離、mlock/mlockall [Phase 2対応]
│
├─ Denial of Service (DoS)
│  └─ 弱点: 認証試行回数制限なし
│     └─ 対策: 指数的バックオフ実装 [Phase 1対応]
│
└─ Elevation of Privilege (権限昇格)
   └─ 弱点: WebUI と CLI の権限分離未実装
      └─ 対策: プロファイルベースのアクセス制御 [Phase 2対応]
```

**攻撃ツリー（Attack Tree）による定量評価**
```
目標: Vault コンテンツの不正アクセス
│
├─ 路線A: パスワード破解
│  ├─ 攻撃コスト: 低～中（辞書攻撃）
│  ├─ 成功確率: 低（エントロピー要件強化で緩和）
│  └─ 影響度: 最大
│
├─ 路線B: 物体スイッチング
│  ├─ 攻撃コスト: 中～高（同等オブジェクト取得）
│  ├─ 成功確率: 中
│  └─ 影響度: 部分的
│
└─ 路線C: メモリダンプ
   ├─ 攻撃コスト: 中～高（物理アクセス + 技術）
   ├─ 成功確率: 低（メモリ保護で緩和）
   └─ 影響度: 最大
```

**実装優先度**: 中（長期プロジェクト）  
**関連Issue**: `[ANALYSIS] STRIDE脅威分析の完成`, `[ANALYSIS] 攻撃ツリーの構築と定量評価`

---

## 実装優先度マトリクス

「ローコスト・高効果」の観点から、実装順序を以下のように推奨します。

| 優先度 | 改善項目 | 理由 | 工数 | 効果 |
|--------|----------|------|-----|-----|
| **最高** | 4. ハッシュチェーン付き監査ログ | 既存`events.log`の拡張で低コスト、改ざん検知は必須 | 1w | ⭐⭐⭐⭐⭐ |
| **最高** | 6. Duress動作の観測不可分性 | ツールの存在意義に直結、タイミング対策は低コスト | 2w | ⭐⭐⭐⭐⭐ |
| **最高** | 9. 暗号的消去の形式化 | `brick`コマンド仕様化のみ、物理削除不要化で実運用効果大 | 3d | ⭐⭐⭐⭐⭐ |
| **高** | 1. FIPS承認KDFへの移行 | 政府利用の入場条件、HKDF-SHA-256は低コスト | 2w | ⭐⭐⭐⭐⭐ |
| **高** | 2. PKCS#11外部トークン対応 | YubiKey等ローコストHSMで実現、鍵管理の分離 | 3w | ⭐⭐⭐⭐ |
| **高** | 5. パスフレーズポリシー強制 | 認証強度の暗号的保証、低コスト実装 | 1w | ⭐⭐⭐⭐ |
| **高** | 7. SBOM自動生成パイプライン | サプライチェーン攻撃への耐性、CI/CD統合で低コスト | 2w | ⭐⭐⭐⭐ |
| **中** | 3. 暗号コアのネイティブ分離 | 工数大だが効果も大、サイドチャネル対策の要 | 4w | ⭐⭐⭐⭐ |
| **中** | 8. WebUIセキュリティ強化 | CSP、ヘッダ設定等は低コスト、プロファイル分離は中程度 | 2w | ⭐⭐⭐ |
| **中** | 10. 脅威モデルの形式化 | ドキュメント作業、Phase 1の基盤 | 3w | ⭐⭐⭐ |
| **長期** | 10. Common Criteria / FIPS認証取得 | 高コスト、政府調達には不可避 | 12m+ | ⭐⭐⭐⭐⭐ |

---

## 実装ロードマップ（推定スケジュール）

### Quarter 1（3ヶ月）: Phase 1 - 内部品質基盤

```
Week 1-2   : 脅威STRIDE分析完了、Issue化
Week 3-4   : 監査ログハッシュチェーン実装
Week 5-6   : Duress動作の観測不可分性実装
Week 7-8   : HKDF-SHA-256への移行実装
Week 9-10  : パスフレーズポリシー実装
Week 11-12 : 静的解析（Bandit/Semgrep）統合、UT網羅率80%達成
             => Phase 1 完了
```

### Quarter 2（3ヶ月）: Phase 2 - 外部検証 + PKCS#11対応

```
Week 1-4   : PKCS#11外部トークン対応実装
Week 5-8   : 独立セキュリティ監査（第三者）
Week 9-12  : 監査結果対応、SBOM統合、WebUI強化
             => Phase 2 完了
```

### Quarter 3-4（6ヶ月）: Phase 3 - ネイティブ分離 + 暗号モジュール化

```
Q3         : 暗号コア（Rust/C）実装、FFI統合
Q4         : メモリ保護（mlock/mlockall）統合、FIPS互換確認
             => Phase 3 完了
```

### Year 2+: Phase 4-5（12ヶ月以上）

```
Phase 4    : FIPS 140-3 Level 1 認証取得準備・申請
Phase 5    : 政府機関運用認定試験
```

---

## 実装チェックリスト

### Phase 1 Issues（優先実装）

- [ ] `[FEAT] STRIDE脅威分析の形式化` → `docs/THREAT_ANALYSIS.md`
- [ ] `[FEAT] ハッシュチェーン付き監査ログ` → `src/phantasm/audit.py`
- [ ] `[FEAT] Duress動作の観測不可分性` → `src/phantasm/emergency_daemon.py`
- [ ] `[FEAT] HKDF-SHA-256への移行` → `src/phantasm/config.py` + `src/phantasm/gv_core.py`
- [ ] `[FEAT] パスフレーズポリシー強制` → `src/phantasm/config.py` + validation
- [ ] `[FEAT] 認証試行制限と指数的バックオフ` → `src/phantasm/web_server.py`
- [ ] `[CI] 静的解析パイプライン（Bandit/Semgrep）` → `.github/workflows/`
- [ ] `[TEST] ユニットテスト網羅率80%以上` → `tests/`

### Phase 2 Issues

- [ ] `[FEAT] PKCS#11対応の外部トークン鍵注入` → `src/phantasm/`
- [ ] `[FEAT] SBOM自動生成パイプライン` → `.github/workflows/`
- [ ] `[FEAT] ビルド再現性の検証` → `Dockerfile` / `build.sh`
- [ ] `[SECURITY] 独立セキュリティ監査` → 外部機関への依頼
- [ ] `[FEAT] WebUI無効化プロファイル` → `src/phantasm/config.py`
- [ ] `[FEAT] セキュリティヘッダの強化` → `src/phantasm/web_server.py`

### Phase 3+ Issues

- [ ] `[FEAT] 暗号コアのRust/C実装への分離` → `cryptasm_core/`
- [ ] `[FEAT] メモリ保護（mlock/mlockall）` → `cryptasm_core/` + `src/phantasm/`
- [ ] `[FEAT] FIPS 140-3 Level 1 準拠設計` → 設計書作成
- [ ] `[SPEC] SSP管理体系の形式化` → `docs/KEY_MANAGEMENT_SPEC.md`
- [ ] `[SPEC] brick コマンドの暗号的消去仕様` → `docs/CRYPTOGRAPHIC_ERASE_SPEC.md`

---

## 設計原則（変わらない）

このロードマップを通じて、以下の原則は**不変**とします：

1. **ローコスト**: 高価なハードウェアHSMではなく、YubiKey等ローコストトークン活用
2. **暗号的消去主戦略**: 物理削除に依存しない、鍵破棄によるアクセス不可能化
3. **OSレベルの利用**: Linux基本機能（dm-crypt、mlock、prctl）の活用
4. **Python+低レイヤーの融合**: ネイティブコアで暗号・メモリを、制御ロジックはPythonで
5. **ドキュメント駆動**: 仕様・脅威分析を先に形式化し、実装時の拠よりどころとする

---

## 結論

Phantasmを軍・諜報機関レベルに引き上げるために最も重要なのは、**暗号アルゴリズムの変更ではなく、その周辺の規律**です。

優先すべき改善は：
1. **鍵素材のライフサイクル管理の厳格化**
2. **メモリ安全性の確保（mlock、explicit_bzero）**
3. **監査証跡の完全性保証（ハッシュチェーン）**
4. **Duress動作の観測不可分性**
5. **これらすべてを支える形式的な脅威分析と第三者検証**

これらは多くが **Phase 1（3ヶ月）で実現可能** であり、総工数は **2～3人月** です。その後の Phase 2-3 で外部検証と規格適合を確保し、最終的に **Year 2+ での政府認定試験取得** を目指します。

「ローコストで守る」という設計思想は十分に堅牢化可能です。必要なのは暗号の追加ではなく、**その周辺の規律と可視性**です。

---

**初版作成**: 2026-05-02  
**著者**: Phantasm Security Hardening Task Force
