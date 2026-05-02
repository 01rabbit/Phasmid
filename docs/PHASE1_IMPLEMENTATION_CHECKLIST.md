# Phase 1 実装 Issue リスト

> 軍用化ロードマップ Phase 1（3ヶ月） の実装タスク一覧

このドキュメントは、`docs/MILITARY_GRADE_HARDENING_ROADMAP.md` の「Phase 1 Issues（優先実装）」を詳細化したものです。

---

## 📋 Issue 作成済み（チェック用）

### [ANALYSIS] STRIDE 脅威分析の形式化

**Issue Title**: 
```
[ANALYSIS] STRIDE脅威分析の形式化と脅威モデルドキュメント作成
```

**説明**: 
- 現在の `docs/THREAT_MODEL.md` を STRIDE フレームワークに基づいて体系化
- 各脅威に対する現在の対策、残存リスク、優先改善を表形式で管理
- 出力ファイル: `docs/THREAT_ANALYSIS_STRIDE.md`

**関連ファイル**:
- `docs/THREAT_MODEL.md`（既存、更新対象）
- `docs/THREAT_ANALYSIS_STRIDE.md`（新規作成）

**テスト**:
- ドキュメントレビュー
- セキュリティチーム確認

---

### [FEAT] ハッシュチェーン付き監査ログ

**Issue Title**:
```
[FEAT] ハッシュチェーン付き監査ログの実装（改ざん検知機能）
```

**説明**:
- 各ログエントリに前エントリのハッシュを含める
- HMAC により整合性を二重保証
- 改ざん・削除の即座検知を可能に

**実装ファイル**:
- `src/phantasm/audit.py` (既存、拡張)
- `src/phantasm/config.py` (設定項目追加)

**仕様**:
```json
{
  "version": "2.0",
  "sequence": 1,
  "timestamp": "2026-05-02T10:30:00Z",
  "event_type": "ui_face_lock_enrolled",
  "source": "web",
  "client_id": "127.0.0.1",
  "previous_hash": "sha256:abc123def456...",
  "entry_hash": "sha256:def456ghi789...",
  "hmac_sha256": "signature..."
}
```

**実装ステップ**:
1. `_compute_entry_hash()` 関数の実装
2. `_compute_entry_hmac()` 関数の実装
3. ログ検証関数 `verify_log_integrity()` の実装
4. `events.log` フォーマットのバージョンアップ
5. ログ読み込み時の自動検証

**テスト**:
- `tests/test_audit.py` に検証ケースを追加
- ハッシュチェーン整合性テスト
- 改ざん検知テスト

**工数**: 1 week

---

### [FEAT] Duress動作の観測不可分性

**Issue Title**:
```
[FEAT] Duress動作のタイミング統一と観測不可分性の実装
```

**説明**:
- 通常アクセス vs Duress アクセスのタイミング差異を排除
- 処理時間をパディングで統一
- エラーメッセージの差異を排除

**実装ファイル**:
- `src/phantasm/emergency_daemon.py` (Duress処理)
- `src/phantasm/web_server.py` (API層の応答時間統一)

**仕様**:
```python
# 目標処理時間: 2.5秒（通常・Duress共通）
# パディングで時間を統一、観測不可能に

def access_vault_indistinguishable(password, mode="normal"):
    """
    mode = "normal" | "duress"
    返り値は統一（メッセージ内容も類似）
    処理時間は常に ~2.5秒
    """
    start = time.time()
    target_duration = 2.5
    
    try:
        if mode == "normal":
            result = vault.unlock(password)
        else:
            result = vault.unlock_duress(password)
    finally:
        elapsed = time.time() - start
        if elapsed < target_duration:
            time.sleep(target_duration - elapsed)
    
    return result
```

**実装ステップ**:
1. タイミング分析（現在の処理時間を測定）
2. 目標処理時間の決定
3. パディング関数の実装
4. Duress動作仕様の文書化（`docs/DURESS_SPEC.md`）
5. 統合テスト

**テスト**:
- `tests/test_emergency_daemon.py` にタイミング検証を追加
- 複数回実行でのばらつき確認（σ < 100ms目標）

**工数**: 2 weeks

---

### [FEAT] HKDF-SHA-256への移行

**Issue Title**:
```
[FEAT] KDF を HKDF-SHA-256 へ移行（NIST準拠化）
```

**説明**:
- 現在の Argon2id を NIST承認KDF（HKDF-SHA-256）に移行
- または、Argon2id + HKDF-SHA-256 の2段構成

**選択肢**:
1. **完全移行**: Argon2id → HKDF-SHA-256
   - メリット: NIST直準拠
   - デメリット: パスワード強度要件が上がる
   
2. **ハイブリッド**: Argon2id → HKDF-SHA-256
   - メリット: Argon2idのメモリ困難性 + NIST準拠
   - デメリット: 複雑度上昇

**推奨**: ハイブリッド構成
```python
# Argon2id でメモリ困難性を確保
kdf_output = argon2_kdf(password, salt)

# HKDF-SHA-256 で NIST準拠化
master_key = hkdf_sha256(
    ikm=kdf_output,
    salt=derived_salt,
    info=b"phantasm-master-key:v1",
    length=32
)

# 子鍵導出
vault_key = hkdf_sha256(
    ikm=master_key,
    salt=derived_salt_2,
    info=b"phantasm-vault-key:v1",
    length=32
)
```

**実装ファイル**:
- `src/phantasm/gv_core.py` (Vault鍵導出)
- `src/phantasm/config.py` (KDF設定)
- `src/phantasm/face_lock.py` (顔ロック鍵導出)

**実装ステップ**:
1. HKDF-SHA-256 ラッパー関数の実装
2. Vault鍵導出ロジックの更新
3. 顔ロック鍵導出ロジックの更新
4. 後方互換性テスト（旧Argon2id形式からのマイグレーション）
5. パスワード強度要件の更新

**テスト**:
- `tests/test_gv_core.py` での導出結果確認
- 後方互換性テスト
- パフォーマンステスト

**工数**: 2 weeks

---

### [FEAT] パスフレーズポリシー強制

**Issue Title**:
```
[FEAT] NIST SP 800-63B準拠のパスフレーズポリシー実装
```

**説明**:
- 最小エントロピー要件：80 bits（推奨）
- 辞書チェック：一般的なパスワード・パスフレーズの除外
- Dicewareモード：推奨される強いパスフレーズ生成

**実装ファイル**:
- `src/phantasm/config.py` (ポリシー設定)
- `src/phantasm/cli.py` (初期化・登録処理)
- `src/phantasm/web_server.py` (Webエンドポイント拡張)

**設定項目**:
```python
PHANTASM_PASSWORD_MIN_ENTROPY = 80  # bits
PHANTASM_PASSWORD_DICTIONARY_CHECK = True
PHANTASM_PASSPHRASE_MODE = "diceware"  # or "standard"
PHANTASM_PASSPHRASE_WORDLIST = "eff_large"  # Diceware辞書
```

**実装ステップ**:
1. エントロピー計算関数の実装
2. 辞書読み込み・チェック機能
3. Diceware生成機能
4. パスワード検証API
5. CLI初期化時の適用

**テスト**:
- `tests/test_config.py` でのポリシー検証
- Diceware生成テスト
- 弱いパスワードの却下確認

**工数**: 1 week

---

### [FEAT] 認証試行制限と指数的バックオフ

**Issue Title**:
```
[FEAT] 認証試行回数制限と指数的バックオフの実装
```

**説明**:
- 5回失敗で60秒ロック
- 次の5回失敗で600秒ロック（10分）
- スライディングウィンドウ式のレート制限

**実装ファイル**:
- `src/phantasm/web_server.py` (API層)
- `src/phantasm/config.py` (設定)

**仕様**:
```python
class AuthenticationLimiter:
    MAX_FAILURES_PER_WINDOW = 5
    BASE_LOCKOUT_DURATION = 60  # 秒
    BACKOFF_MULTIPLIER = 10  # 次ウィンドウ毎に 10倍
    
    def check_attempt(self, client_id):
        failures = self.get_failure_count(client_id)
        if failures >= self.MAX_FAILURES_PER_WINDOW:
            window_number = failures // self.MAX_FAILURES_PER_WINDOW
            lockout = self.BASE_LOCKOUT_DURATION * (self.BACKOFF_MULTIPLIER ** (window_number - 1))
            if self.is_locked(client_id, lockout):
                raise AuthenticationLockedError(lockout)
```

**適用対象**:
- `/face/verify` (顔認証)
- `/restricted/confirm` (制限確認)
- ログインAPI（将来拡張時）

**実装ステップ**:
1. ロック状態の管理（Redis or メモリ）
2. 試行回数のカウント
3. 指数的バックオフ計算
4. API層での適用

**テスト**:
- `tests/test_web_server.py` での制限テスト
- バックオフ計算確認

**工数**: 1 week

---

### [CI] 静的解析パイプライン（Bandit/Semgrep）

**Issue Title**:
```
[CI] GitHub Actions での静的解析パイプライン構築
```

**説明**:
- `bandit`: Python セキュリティ脆弱性検査
- `semgrep`: 規則ベースのコード解析
- PR毎に自動実行、問題を検出・報告

**実装ファイル**:
- `.github/workflows/static-analysis.yml` (新規作成)

**パイプライン仕様**:
```yaml
name: Static Analysis

on: [push, pull_request]

jobs:
  bandit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install bandit
      - run: bandit -r src/ -f json -o bandit-report.json
      - uses: actions/upload-artifact@v3
        with:
          name: bandit-report
          path: bandit-report.json
  
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/python
```

**実装ステップ**:
1. bandit 設定 (`.bandit`)
2. semgrep 規則設定 (`.semgrep.yml`)
3. GitHub Actions ワークフロー作成
4. 既存コード修正（既知の問題対応）

**テスト**:
- ローカルでの bandit/semgrep 実行確認
- PR作成時にワークフロー実行確認

**工数**: 1 week

---

### [TEST] ユニットテスト網羅率80%以上

**Issue Title**:
```
[TEST] ユニットテスト網羅率を80%以上に引き上げ
```

**説明**:
- 現在の網羅率を測定
- 不足しているテストケースを追加
- カバレッジリポートを CI に統合

**実装ファイル**:
- `tests/` (既存、拡張)
- `.github/workflows/coverage.yml` (新規作成)

**実装ステップ**:
1. `coverage.py` による計測
2. カバレッジ測定結果の分析
3. 不足ケースの実装
4. CI 統合

**ターゲット**:
```
src/phantasm/:
  - config.py: 85%
  - audit.py: 90%
  - gv_core.py: 80%
  - face_lock.py: 85%
  - web_server.py: 75%
  - cli.py: 80%
  → 平均 82%
```

**テスト**:
- `pytest --cov=src tests/`

**工数**: 2-3 weeks

---

## 📊 Phase 1 実装スケジュール（推奨）

```
Week 1-2   : [ANALYSIS] STRIDE分析 + Issue化
Week 3-4   : [FEAT] ハッシュチェーン監査ログ
Week 5-6   : [FEAT] Duress観測不可分性
Week 7-8   : [FEAT] HKDF-SHA-256移行
Week 9-10  : [FEAT] パスフレーズポリシー + 認証制限
Week 11-12 : [CI] 静的解析 + [TEST] テスト網羅率80%
             → Phase 1 完了
```

**パラレル実施可能**:
- Week 3-: 複数の [FEAT] は並行実施可（6-8人月で3ヶ月達成）

---

## 🚀 Issue 作成手順

GitHub で Issue を作成する際：

1. 本リストから該当する Issue タイトルをコピー
2. [Hardening Feature テンプレート](./.github/ISSUE_TEMPLATE/hardening-feature.md) を使用
3. 上記詳細を Description に記入
4. ラベル: `hardening`, `phase-1` を付与
5. プロジェクトボード に追加（存在する場合）

---

## 📝 チェックリスト（進捗管理用）

### [ANALYSIS] STRIDE 脅威分析
- [ ] Issue 作成完了
- [ ] 実装開始
- [ ] ドキュメント作成
- [ ] セキュリティチーム確認
- [ ] マージ

### [FEAT] ハッシュチェーン監査ログ
- [ ] Issue 作成完了
- [ ] 仕様レビュー
- [ ] 実装完了
- [ ] テスト通過
- [ ] マージ

### [FEAT] Duress観測不可分性
- [ ] Issue 作成完了
- [ ] 仕様レビュー
- [ ] 実装完了
- [ ] タイミング検証
- [ ] マージ

（以下、同様に）

---

## 参考資料

- [軍用化ロードマップ](./MILITARY_GRADE_HARDENING_ROADMAP.md)
- [脅威モデル](./THREAT_MODEL.md)
- NIST SP 800-63B: Authentication
- NIST SP 800-30: Risk Assessment
- Microsoft STRIDE Threat Modeling
