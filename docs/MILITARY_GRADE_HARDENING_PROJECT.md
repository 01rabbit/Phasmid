# 🛡️ Phantasm 軍用化（Military Grade Hardening）プロジェクト

**プロジェクト開始日**: 2026-05-02  
**目標完了**: 2027-09 (Phase 1-3) → 2028-09 (Phase 4, 政府認定)

---

## 📖 プロジェクト概要

Phantasm を軍・政府諜報機関の運用基準（FIPS 140-3, NIST SP 800系, NSA CSfC等）に適合させるための包括的な改善プロジェクトです。

「ローコストで守る」という設計思想を維持しつつ、**鍵管理、メモリ安全性、監査、Duress対策、形式的脅威分析**の領域で大幅な硬化を実現します。

---

## 📚 ドキュメント構成

| ドキュメント | 用途 | 対象 |
|------------|------|------|
| **[軍用化ロードマップ](./MILITARY_GRADE_HARDENING_ROADMAP.md)** | 全体戦略・10領域の改善目標 | PL、セキュリティ責任者 |
| **[Phase 1 実装チェックリスト](./PHASE1_IMPLEMENTATION_CHECKLIST.md)** | 具体的な Issue・スケジュール | 開発チーム |
| **[Issue テンプレート: Hardening Feature](../.github/ISSUE_TEMPLATE/hardening-feature.md)** | 機能実装 Issue の標準フォーマット | Issue 作成者 |
| **[Issue テンプレート: Security Analysis](../.github/ISSUE_TEMPLATE/security-analysis.md)** | 脅威分析 Issue の標準フォーマット | セキュリティ分析者 |

---

## 🎯 Phase 別目標

### Phase 1（3ヶ月）: 内部品質基盤
```
✅ 脅威STRIDE分析の形式化
✅ ハッシュチェーン監査ログ実装
✅ Duress動作の観測不可分性確保
✅ HKDF-SHA-256への移行
✅ パスフレーズポリシー強制
✅ 認証試行制限＋指数的バックオフ
✅ 静的解析パイプライン（Bandit/Semgrep）統合
✅ ユニットテスト網羅率80%以上

=> 内部セキュリティ基盤の完成
```

**関連 Issues**: 8個  
**推定工数**: 2～3人月  
**優先度**: **最高**

---

### Phase 2（3ヶ月）: 外部検証 + PKCS#11対応
```
✅ PKCS#11外部トークン対応（YubiKey等）
✅ SBOM自動生成パイプライン統合
✅ ビルド再現性検証
✅ 独立セキュリティ監査（第三者）
✅ WebUI無効化プロファイル
✅ セキュリティヘッダ強化
✅ セッション短寿命化

=> 政府利用対応＆外部検証完了
```

**関連 Issues**: 7個  
**推定工数**: 3～4人月  
**優先度**: **高**

---

### Phase 3（6ヶ月）: ネイティブ分離 + 暗号モジュール化
```
✅ 暗号コアのRust/C実装への分離
✅ メモリ保護（mlock/mlockall）統合
✅ 定数時間比較・サイドチャネル対策
✅ FIPS 140-3 Level 1 準拠設計
✅ SSP（鍵）管理体系の形式化
✅ Cryptographic Erase仕様化

=> 高度なセキュリティ実装完成
```

**関連 Issues**: 6個  
**推定工数**: 4～5人月  
**優先度**: **中**

---

### Phase 4-5（12ヶ月以上）: 認証取得
```
✅ FIPS 140-3 Level 1 認証取得
✅ Common Criteria 評価（EAL2+）
✅ 政府機関運用認定

=> 公式認定・政府調達対応
```

**推定工数**: 6～12人月  
**優先度**: **長期目標**

---

## 🚀 クイックスタート

### 1. ロードマップの理解（30分）
```bash
# 全体戦略を確認
open docs/MILITARY_GRADE_HARDENING_ROADMAP.md
```

### 2. Phase 1 実装計画の確認（1時間）
```bash
# 具体的なタスクと優先度を確認
open docs/PHASE1_IMPLEMENTATION_CHECKLIST.md
```

### 3. Issue の作成（15分/個）
```bash
# GitHub でIssue作成
# テンプレート: .github/ISSUE_TEMPLATE/hardening-feature.md
# または: .github/ISSUE_TEMPLATE/security-analysis.md

# 例: "STRIDE脅威分析"
# 例: "ハッシュチェーン監査ログ"
# 例: "Duress観測不可分性"
# ... (Phase 1の8個をすべて作成)
```

### 4. プロジェクトボードの設定（オプション）
```bash
# GitHub Projects で作成
# タイトル: "Phantasm Military-Grade Hardening"
# ビュー: Phase 1, Phase 2, Phase 3, Backlog
# 各 Issue を該当 Phase に割り当て
```

### 5. 開発開始（Week 1）
```bash
# Phase 1 の優先 Issue から順に開発開始
# 推奨順序:
# 1. STRIDE 脅威分析
# 2. ハッシュチェーン監査ログ
# 3. Duress 観測不可分性
# ...
```

---

## 📋 Issue 作成テンプレート（コピペ用）

### Issue タイプ1: 機能実装（Hardening Feature）

```markdown
---
name: "🛡️ Hardening Feature (軍用化改善)"
---

**関連領域**: 4. 監査ログとフォレンジック対応
**改善項目**: ハッシュチェーン付き監査ログ
**実装優先度**: 最高

## 問題の背景
現在の events.log は改ざん検知機能がなく、政府・軍の監査基準に適合しない。

## 提案する改善
各ログエントリに前エントリのハッシュを含める（ハッシュチェーン）。
HMAC で整合性を二重保証し、改ざん・削除の即座検知を可能にする。

## 実装仕様
[PHASE1_IMPLEMENTATION_CHECKLIST.md の該当セクションを参照]

## テスト計画
- ユニットテスト: ハッシュ計算、チェーン検証
- 統計分析テスト: 改ざん時の検知確認

## 評価基準
- [ ] 実装仕様に従ったコード変更
- [ ] 全テストケース通過
- [ ] ドキュメント更新完了
```

### Issue タイプ2: 脅威分析（Security Analysis）

```markdown
---
name: "🔍 Security Analysis (脅威分析)"
---

**分析対象**: UI顔認証フロー
**スコープ**: 初回登録～認証～ダッシュボードアクセス

## STRIDE 分析
[各脅威について詳細記述]

## 攻撃ツリー
[階層的な攻撃パスを図示]

## リスク評価マトリクス
[尤度・影響度・優先度を記入]

## 推奨改善
- Phase 1: ...
- Phase 2: ...
- Phase 3+: ...
```

---

## 📊 進捗管理用チェックリスト

### Phase 1（3ヶ月）

#### Week 1-2: 脅威分析
- [ ] STRIDE フレームワーク適用
- [ ] Issue: `[ANALYSIS] STRIDE脅威分析` 作成
- [ ] ドキュメント: `docs/THREAT_ANALYSIS_STRIDE.md` 作成

#### Week 3-4: 監査ログ
- [ ] Issue: `[FEAT] ハッシュチェーン監査ログ` 作成・実装開始
- [ ] `src/phantasm/audit.py` 修正
- [ ] テスト追加
- [ ] PR マージ

#### Week 5-6: Duress対策
- [ ] Issue: `[FEAT] Duress観測不可分性` 作成・実装開始
- [ ] タイミング分析
- [ ] パディング実装
- [ ] テスト・マージ

#### Week 7-8: KDF移行
- [ ] Issue: `[FEAT] HKDF-SHA-256移行` 作成・実装開始
- [ ] `src/phantasm/gv_core.py` 修正
- [ ] 後方互換性テスト
- [ ] マージ

#### Week 9-10: ポリシー + 認証制限
- [ ] Issue: `[FEAT] パスフレーズポリシー` 作成・実装
- [ ] Issue: `[FEAT] 認証試行制限` 作成・実装
- [ ] マージ

#### Week 11-12: CI + テスト
- [ ] Issue: `[CI] 静的解析パイプライン` 作成・実装
- [ ] Issue: `[TEST] テスト網羅率80%` 作成・実装
- [ ] **Phase 1 完了✅**

---

## 🔐 セキュリティ原則（変わらない）

このプロジェクトを通じて、以下の設計原則は**不変**とします：

1. **ローコスト**: 高価なハードウェアHSMではなく、YubiKey等ローコストトークン活用
2. **暗号的消去**: 物理削除に依存しない、鍵破棄によるアクセス不可能化
3. **OSレベル活用**: Linux基本機能（dm-crypt、mlock、prctl）の活用
4. **Python+ネイティブ**: ネイティブコアで暗号・メモリを、制御ロジックはPythonで
5. **ドキュメント駆動**: 仕様・脅威分析を先に形式化し、実装時の拠所とする

---

## 💡 実装のヒント

### ローカル脅威分析のやり方
```bash
# STRIDE フレームワークの適用手順:
# 1. システムの各構成要素を抽出（UI, API, 鍵管理等）
# 2. 各構成要素について S-T-R-I-D-E の脅威を列挙
# 3. 現在の対策を整理
# 4. リスク評価（高/中/低）
# 5. 改善提案（Phase 1-5で優先順位付け）

# 参考: Microsoft Threat Modeling Tool
# https://www.microsoft.com/en-us/securityengineering/sdl/threatmodeling
```

### ハッシュチェーン監査ログの実装のコツ
```python
# 1. 前エントリのハッシュを現在のエントリに含める
# 2. HMAC で全体を署名
# 3. ログ読み込み時に自動検証
# 4. 改ざん検知時は警告ログ出力 + 管理者通知

# 参考: RFC 3161 Time-Stamp Protocol (TSP)
# 参考: NIST SP 800-154: Guidelines for Implementing Cryptography
```

### Duress動作のタイミング統一のコツ
```python
# 1. 目標処理時間を決定（例: 2.5秒）
# 2. 通常・Duress両方で同じ処理時間を計測
# 3. 時間が足りなければ sleep() でパディング
# 4. 複数回実行でばらつき確認（σ < 100ms目標）

# 参考: Constant-Time Cryptography
# https://bearssl.org/ctmul.html
```

---

## 📞 質問・相談

- **セキュリティ設計について**: `[DISCUSSION] Military-Grade Hardening Design` Issue を作成
- **進捗報告**: PR コメントまたは `[UPDATE] Phase 1 進捗` Issue で報告
- **ロードマップ修正提案**: PR で `docs/MILITARY_GRADE_HARDENING_ROADMAP.md` を修正

---

## 🎓 参考資料

### 暗号・セキュリティ標準
- NIST SP 800-53: Security and Privacy Controls
- NIST SP 800-63B: Authentication and Lifecycle Management
- NIST SP 800-30: Guide for Conducting Risk Assessments
- NIST SP 800-90A: Recommendation for Random Number Generation
- FIPS 140-3: Implementation Guidance for FIPS 140-3
- NSA Commercial Cloud Services (CSfC) Data at Rest

### 脅威分析フレームワーク
- Microsoft STRIDE: https://www.microsoft.com/security/blog/2007/09/11/stride-chart/
- OWASP Threat Modeling: https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html
- Attack Trees: https://en.wikipedia.org/wiki/Attack_tree

### コードセキュリティ
- Bandit: https://bandit.readthedocs.io/
- Semgrep: https://semgrep.dev/
- OWASP Top 10: https://owasp.org/www-project-top-ten/

---

## 📄 ライセンス・著作権

このドキュメント・プロジェクトは Phantasm リポジトリの既存ライセンスに従います。

**初版作成**: 2026-05-02  
**最終更新**: 2026-05-02  
**著者**: Phantasm Security Hardening Task Force

---

**お疲れ様です。大規模なセキュリティハードニングプロジェクトへようこそ！** 🚀
