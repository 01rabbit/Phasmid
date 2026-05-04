# Phasmid WebUI — Design Proposal

## 概要

このドキュメントは Phasmid WebUI の再設計に向けたデザイン案・コンポーネント構成・画面トーンを定義する。  
ロゴのビジュアルアイデンティティを基点に、フィールドオペレーション用ツールとしての機能美と視認性を両立させる。

---

## 1. デザインコンセプト：「Operational Ghost」

### ロゴから読み取るブランドアイデンティティ

ロゴの構成要素：

| 要素 | 意味 | デザインへの反映 |
|------|------|----------------|
| ナナフシ（Phasmid）シルエット | 擬態・不可視性・自然 | 「見えないが機能する」UI |
| 回路基板トレース | デジタル精度・工学的設計 | グリッド・精密なライン使い |
| キーホール（胸部中央） | アクセス制御・鍵管理 | ロック/アンロックの明確な視覚表現 |
| 円形ボーダーとドット | 範囲・境界・精度 | ステータスのLEDドット表現 |
| ダーク背景 × オリーブグリーン | 戦術的・フィールド的 | カラーパレットの根幹 |

### コンセプト三原則

1. **Invisible by Design** — UIはコンテンツを邪魔しない。最小限のクロームで情報を前面に出す
2. **Tactical Precision** — すべての要素は目的を持つ。装飾的なノイズを排除し、状態変化を明確に伝える
3. **Organic-meets-Digital** — ロゴの「生物 × 回路」のように、有機的な余白と機械的な精度を共存させる

---

## 2. カラーシステム（Design Tokens）

### 背景・サーフェス

```css
--bg-void:    #070c09;   /* ページ最深部 ― ロゴ背景と同系 */
--bg-base:    #0b1210;   /* プライマリ背景 */
--bg-surface: #101a12;   /* パネル・カード */
--bg-raised:  #162018;   /* 浮き上がったコンポーネント（インプット等） */
--bg-overlay: #1d2c1e;   /* ホバー・アクティブ状態 */
```

### ボーダー・区切り

```css
--border:       #243424;  /* デフォルトボーダー */
--border-soft:  #1a261a;  /* 微細な区切り */
--border-focus: #4a7038;  /* フォーカス・アクティブ */
--border-accent:#6a9848;  /* アクセントカラーボーダー */
```

### テキスト

```css
--text-primary:   #c8d8b0;  /* 本文 ― オリーブがかった白 */
--text-secondary: #849870;  /* サブ情報 */
--text-muted:     #4e6244;  /* ラベル・ウォーターマーク */
--text-danger:    #e8a0a0;  /* 警告テキスト */
```

### アクセント（ロゴのナナフシ体色から抽出）

```css
--accent:       #7aaa48;  /* 主アクセント ― ロゴとの同一性 */
--accent-dim:   #4a7028;  /* 背景用アクセント */
--accent-bright:#b0dc68;  /* 最高輝度 ― アクティブLED、ライブ表示専用 */
```

### ステータスカラー

```css
--status-ready:   #50cc84;  /* 準備完了・成功 */
--status-active:  #7aaa48;  /* 動作中 */
--status-caution: #c89c36;  /* 注意・アンバー */
--status-alert:   #cc4040;  /* 危険・エラー */
--status-off:     #3a4e38;  /* 無効・不明 */
```

### 特殊用途

```css
--phosphor:   #aaee40;   /* 生体ライブ表示のみ（カメラLED等）*/
--camera-bg:  #040808;   /* カメラフィード背景 */
--glow-accent:rgba(122,170,72,0.18);  /* アクセントグロー */
--glow-ready: rgba(80,204,132,0.20);  /* Ready状態グロー */
--glow-alert: rgba(204,64,64,0.16);   /* アラートグロー */
```

### カラーマッピング（現行 → 新規）

| 現行変数 | 現行値 | 新規変数 | 新規値 | 変更の意図 |
|---------|--------|---------|--------|-----------|
| `--bg` | `#0e1116` | `--bg-base` | `#0b1210` | 青みを除きロゴ背景と統一 |
| `--panel` | `#171b22` | `--bg-surface` | `#101a12` | 緑系に |
| `--blue` | `#4f8cff` | `--accent` | `#7aaa48` | ブランドカラーへ転換 |
| `--green` | `#3ddc97` | `--status-ready` | `#50cc84` | 整理 |
| `--muted` | `#9aa7b6` | `--text-secondary` | `#849870` | 温かみのある中間色 |

---

## 3. タイポグラフィシステム

### フォントスタック

```css
/* ヘッダー・ナビゲーション・セクション見出し */
--font-heading: "Space Grotesk", "Barlow", Inter, -apple-system, sans-serif;

/* 本文・フォーム */
--font-body: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;

/* コードボックス・ログ・イベント */
--font-mono: "JetBrains Mono", "IBM Plex Mono", Consolas, monospace;
```

> Space Grotesk はオプション（オフライン環境では Inter fallback で一貫性を維持）。  
> `font-feature-settings: "tnum" 1;` を数値表示に適用してラインを揃える。

### タイプスケール

```css
--text-xs:   11px;  /* カードラベル、LED下注記 */
--text-sm:   13px;  /* 補足コピー、フォームラベル */
--text-base: 14px;  /* 本文 */
--text-md:   16px;  /* パネルヘッダー */
--text-lg:   20px;  /* ページタイトル（ブランド名） */
--text-xl:   28px;  /* 大きなステータス表示 */
```

### 文字間隔

```css
/* 通常本文 */
letter-spacing: 0;

/* セクションラベル（h3、カードラベルなど）*/
letter-spacing: 0.08em;
text-transform: uppercase;

/* ブランドロゴ文字 */
letter-spacing: 0.04em;
```

---

## 4. ビジュアル言語

### 4-1. エッジ処理

現行の `border-radius: 8px` を用途に応じて使い分ける。

```css
--radius-sm:  2px;   /* インライン要素（バッジ等）*/
--radius-md:  4px;   /* パネル・カード ― 硬質なエッジで戦術的印象 */
--radius-lg:  6px;   /* インプット・ボタン */
--radius-pill:999px; /* ステータスLED */
```

### 4-2. パネル左アクセントライン

パネルの左端に細い縦ラインを加え、情報の階層を強調する。

```css
.panel {
    border-left: 2px solid var(--border-accent);
}
.panel--danger {
    border-left-color: var(--status-alert);
    background: color-mix(in srgb, var(--bg-surface) 94%, var(--status-alert) 6%);
}
.panel--caution {
    border-left-color: var(--status-caution);
}
```

### 4-3. カメラフィード HUD

戦術的サーベイランスモニターの見た目。  
CSSの `::before` / `::after` と追加の疑似要素でコーナーブラケットを描く。

```
┌─ Camera Preview ─────────────────┐
│ ┌───┐                      ┌───┐ │
│ │           [LIVE]          │   │
│ │                            │   │
│ │      [camera feed]         │   │
│ │                            │   │
│ └───┘                      └───┘ │
│  Object: ● Stable match          │
└──────────────────────────────────┘
```

```css
.camera-frame {
    position: relative;
    background: var(--camera-bg);
}
/* コーナーブラケットは疑似要素でL字型に */
.camera-frame::before,
.camera-frame::after {
    content: '';
    position: absolute;
    width: 18px;
    height: 18px;
    border-color: var(--accent);
    border-style: solid;
    opacity: 0.7;
}
.camera-frame::before { top: 8px; left: 8px; border-width: 2px 0 0 2px; }
.camera-frame::after  { top: 8px; right: 8px; border-width: 2px 2px 0 0; }
/* 下コーナーは .camera-frame 内の追加要素で対応 */
```

### 4-4. LED ステータスドット

カードやバッジの代わりに、小さなLEDドットで状態を視覚化。

```css
.led {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: var(--radius-pill);
    background: var(--status-off);
}
.led--ready   { background: var(--status-ready);   box-shadow: 0 0 6px var(--glow-ready); }
.led--active  { background: var(--accent-bright);  box-shadow: 0 0 8px var(--glow-accent); }
.led--caution { background: var(--status-caution); box-shadow: 0 0 5px rgba(200,156,54,.4); }
.led--alert   { background: var(--status-alert);   box-shadow: 0 0 6px var(--glow-alert); }
```

### 4-5. サブテキストラベル（セクションヘッダー）

```css
.section-label {
    font-size: var(--text-xs);
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--text-muted);
    font-weight: 600;
}
```

---

## 5. レイアウト構造

### 5-1. トップバー（ブランドエリア）

現行のテキストのみのブランドを、ロゴ画像を使用した形式に変更。

```
┌──────────────────────────────────────────────────────────────────┐
│  [🪲ロゴ小] Phasmid          [Home] [Store] [Retrieve] [Maint.] │
│             Local-only protected storage interface                │
└──────────────────────────────────────────────────────────────────┘
```

```css
.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}
.brand-logo {
    width: 36px;
    height: 36px;
    object-fit: contain;
    opacity: 0.92;
    filter: drop-shadow(0 0 6px var(--glow-accent));
}
.brand-text h1 {
    font-size: var(--text-lg);
    letter-spacing: 0.04em;
    margin: 0 0 2px;
    color: var(--text-primary);
}
.brand-text p {
    font-size: var(--text-xs);
    color: var(--text-muted);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 0;
}
```

### 5-2. ナビゲーション

現行のボーダーボタン形式から、アンダーラインベースのタブ形式に変更。

```css
.nav a {
    color: var(--text-muted);
    padding: 8px 14px;
    font-size: 13px;
    letter-spacing: 0.04em;
    border-bottom: 2px solid transparent;
    transition: color .15s, border-color .15s;
}
.nav a:hover {
    color: var(--text-primary);
}
.nav a.active {
    color: var(--accent-bright);
    border-bottom-color: var(--accent);
}
```

### 5-3. ステータスグリッド

4ステータスカードを「モジュールインジケーター」として再設計。  
LEDドット + ラベル + 値の3層構造。

```
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ ● DEVICE   │ │ ● CAMERA   │ │ ● OBJECT   │ │ ● MODE     │
│ Ready      │ │ Active     │ │ Stable     │ │ Local-only │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

```css
.status-card {
    padding: 14px 16px;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    border-left: 2px solid var(--border-accent);
    background: var(--bg-surface);
    display: grid;
    gap: 6px;
}
.status-card__header {
    display: flex;
    align-items: center;
    gap: 7px;
}
/* LED + ラベル */
.status-card__value {
    font-size: var(--text-xl);
    font-weight: 700;
    font-feature-settings: "tnum" 1;
    color: var(--text-primary);
    line-height: 1.1;
}
```

---

## 6. コンポーネント構成

### 6-1. コンポーネント一覧

| コンポーネント | クラス名 | 説明 |
|------------|---------|------|
| ページシェル | `.shell` | 最大幅コンテナ |
| トップバー | `.topbar` | ブランド + ナビ |
| ブランドブロック | `.brand` | ロゴ + 名前 + サブタイトル |
| ナビゲーション | `.nav` | ページリンク群 |
| グリッドレイアウト | `.layout-grid` | 2カラム（カメラ + コンテンツ） |
| シングルレイアウト | `.layout-stack` | 縦積みレイアウト |
| パネル | `.panel` | コンテンツカード |
| パネル（危険） | `.panel--danger` | 破壊的操作用 |
| パネル（注意） | `.panel--caution` | 注意喚起用 |
| ステータスグリッド | `.status-grid` | 4カラムステータス |
| ステータスカード | `.status-card` | 個別ステータス表示 |
| LEDドット | `.led` | 状態インジケーター |
| カメラフレーム | `.camera-frame` | HUDカメラパネル |
| バッジ | `.badge` | インラインラベル |
| フィールド | `.field` | ラベル + インプット |
| ボタン（主） | `.btn` | プライマリアクション |
| ボタン（副） | `.btn--secondary` | セカンダリ |
| ボタン（危険） | `.btn--danger` | 破壊的アクション |
| ボタン（ゴースト） | `.btn--ghost` | 最小存在感 |
| コードボックス | `.codebox` | ログ・診断出力 |
| 警告ストリップ | `.warning-strip` | 破壊的警告 |
| トースト通知 | `.toast` | 一時通知 |
| セクションラベル | `.section-label` | 区切り見出し |

### 6-2. ボタン定義

```css
/* Base */
.btn {
    cursor: pointer;
    font: inherit;
    font-size: 13px;
    font-weight: 650;
    padding: 10px 16px;
    border-radius: var(--radius-lg);
    border: 1px solid;
    letter-spacing: 0.03em;
    transition: background .12s, box-shadow .12s;
}

/* Primary — アクセントグリーン */
.btn {
    color: #0b1210;
    background: var(--accent);
    border-color: #5a8838;
}
.btn:hover {
    background: var(--accent-bright);
    box-shadow: 0 0 12px var(--glow-accent);
}

/* Secondary */
.btn--secondary {
    color: var(--text-secondary);
    background: var(--bg-raised);
    border-color: var(--border);
}
.btn--secondary:hover {
    color: var(--text-primary);
    border-color: var(--border-focus);
}

/* Danger */
.btn--danger {
    color: #f8d0d0;
    background: #5a1c1c;
    border-color: var(--status-alert);
}
.btn--danger:hover {
    background: #7a2020;
    box-shadow: 0 0 10px var(--glow-alert);
}

/* Ghost */
.btn--ghost {
    color: var(--text-muted);
    background: transparent;
    border-color: transparent;
}
.btn--ghost:hover {
    color: var(--text-secondary);
    border-color: var(--border);
}

/* Small modifier */
.btn--sm { padding: 7px 11px; font-size: 12px; }
```

### 6-3. フォーム要素

```css
input, select, textarea {
    font: inherit;
    font-size: var(--text-base);
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    color: var(--text-primary);
    padding: 10px 12px;
    width: 100%;
    transition: border-color .12s, box-shadow .12s;
}
input:focus, select:focus {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: 0 0 0 3px rgba(74,112,56,.20);
}
input::placeholder { color: var(--text-muted); }
```

### 6-4. バッジ

```css
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border: 1px solid;
    font-weight: 600;
}
/* バッジ内にLEDドットを含められる: <span class="badge good"><span class="led led--ready"></span>Ready</span> */
.badge.good    { color: var(--status-ready);   border-color: rgba(80,204,132,.35); background: rgba(80,204,132,.08); }
.badge.warn    { color: var(--status-caution); border-color: rgba(200,156,54,.35); background: rgba(200,156,54,.08); }
.badge.bad     { color: var(--status-alert);   border-color: rgba(204,64,64,.35);  background: rgba(204,64,64,.08); }
.badge.neutral { color: var(--text-muted);     border-color: var(--border); }
.badge.active  { color: var(--accent-bright);  border-color: rgba(122,170,72,.40); background: rgba(122,170,72,.10); }
```

### 6-5. 警告ストリップ

```css
.warning-strip {
    display: flex;
    gap: 10px;
    padding: 10px 14px;
    border-left: 3px solid var(--status-alert);
    background: rgba(204,64,64,.08);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    color: var(--text-danger);
    font-size: var(--text-sm);
    line-height: 1.55;
    margin-bottom: 14px;
}
```

### 6-6. Jinja2 マクロ拡張

既存の `_components.html` マクロを拡張：

```jinja2
{# LEDインジケーター付きステータスカード #}
{% macro status_card(title, value_id, value, led_class="") -%}
<section class="status-card">
    <div class="status-card__header">
        <span class="led {{ 'led--' + led_class if led_class else '' }}" id="{{ value_id }}Led"></span>
        <span class="section-label">{{ title }}</span>
    </div>
    <strong class="status-card__value" id="{{ value_id }}">{{ value }}</strong>
</section>
{%- endmacro %}

{# HUDカメラフレーム #}
{% macro camera_frame(src="/video_feed", label="Camera Preview") -%}
<section class="panel camera-panel">
    <div class="panel-head">
        <h2>{{ label }}</h2>
        <span id="objectBadge" class="badge neutral">
            <span class="led"></span>Unavailable
        </span>
    </div>
    <div class="camera-frame">
        <img class="camera-feed" src="{{ src }}" alt="Local camera preview">
        <div class="camera-frame__corners">
            <span class="corner corner--tl"></span>
            <span class="corner corner--tr"></span>
            <span class="corner corner--bl"></span>
            <span class="corner corner--br"></span>
        </div>
        <div class="camera-live-indicator">
            <span class="led led--active"></span>
            <span class="section-label">Live</span>
        </div>
    </div>
</section>
{%- endmacro %}
```

---

## 7. 画面別トーン定義

### 7-1. Home（オペレーション概要）

**トーン**: ミッションコントロール。準備完了確認。  
**支配色**: アクセントグリーン（Ready状態）  
**重点**: ステータスグリッド + ライブカメラ

```
ステータスグリッド（4カード）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Camera Preview + HUD]  │  [Protected Entry Console]
  ● LIVE                │  
  ┌─┐ ┌─┐              │  Create or unlock a protected
  │           │         │  entry using an access password
  └─┘ └─┘              │  and bound physical object.
  Object: ● Stable match│
                        │  [Store] [Retrieve] [Maintenance]
                        │
                        │  RECENT LOCAL EVENT
                        │  Waiting for local operation.
```

### 7-2. Store（保護エントリ作成）

**トーン**: 作業中。カメラが中核。フォームが副。  
**支配色**: カメラ枠にアクセント強調（オブジェクトキャプチャ時）  
**重点**: キャプチャー完了まで「Save entry」ボタンは視覚的に抑制

```
[Camera Preview]        │  Create Protected Entry
  ↑ Object capture      │  ─────────────────────
  focus ここ             │  File to protect: [__________]
                         │  Access password: [__________]
                         │  ▶ Advanced
                         │
                         │  [Check metadata] [Scrub copy]
                         │  [▣ Capture object]   ← 強調
                         │  [Save entry ●]
```

**オブジェクトキャプチャ後の状態変化**:
- カメラ枠のコーナーブラケットが `--accent-bright` に発光
- Object バッジが `good` に遷移
- 「Save entry」ボタンが `--accent` の通常スタイルに活性化

### 7-3. Retrieve（取得）

**トーン**: 集中・意図的。パスワード入力が焦点。  
**支配色**: ニュートラル（解錠前） → グリーン（成功後）  
**重点**: 不要な情報を排除し、パスワードフィールドのみ際立たせる

```
[Camera Preview]        │  Retrieve Protected Entry
  Object: ● Stable      │  ─────────────────────
                         │  Access password: [__________]
                         │
                         │  [Retrieve]
                         │
                         │  ┌──────────────────────────┐
                         │  │ Download ready            │
                         │  │ [⬇ Download file]         │
                         │  └──────────────────────────┘
```

### 7-4. Maintenance（メンテナンス）

**トーン**: 技術ターミナル。管理者向け。  
**支配色**: アンバー（注意・メンテナンス中）  
**重点**: 診断ログはモノスペースで。アクション間のセパレーターを明確に

- パネル左アクセントラインを `--status-caution`（アンバー）に設定
- セクションラベルの間隔を広め（32px）に設定し、操作ミスを防ぐ

### 7-5. Entry Management（エントリ管理）

**トーン**: 設定・構成。カメラは補助的。  
**支配色**: ニュートラル  
**重点**: エントリステータスをLEDで一覧表示

### 7-6. Emergency / Restricted Actions（制限アクション）

**トーン**: 最終手段。重大な結果。抑制されたが重いレッド。  
**支配色**: `--status-alert`（深い赤）  
**重点**: 各アクションを `.panel--danger` で包み、視覚的に完全に分離

```
┌──────────────────────────────────────────────────────┐
│ border-left: 2px solid var(--status-alert)           │
│ Restricted Actions                ⚠ Local data risk  │
│ ▶ Restricted confirmation [_________________________] │
│   [Confirm local control]                            │
└──────────────────────────────────────────────────────┘

（確認後に展開）
┌──────────────────────────────────────────────────────┐
│ !! Clear Unmatched Entry                             │
│ !! Initialize Local Container                        │
│ !! Clear Local Access Path                           │
└──────────────────────────────────────────────────────┘
```

- `--bg-void` に近い暗さで全体を沈める（`.shell` の background を一段暗く）
- 通常ナビゲーションへのリンクは省略（戻るのに明示的な操作が必要）

### 7-7. UI Lock（顔認証ゲート）

**トーン**: バイオメトリックゲート。隠蔽・コンシールド。  
**支配色**: 完全なダーク、ロゴグロー  
**重点**: カメラが全画面に近い存在感。最小テキスト

```
┌────────────────────┬────────────────┐
│                    │  UI Lock       │
│  [Camera - large]  │  ─────         │
│   ┌─┐       ┌─┐  │  Face UI lock  │
│                    │  controls...   │
│   └─┘       └─┘  │                │
│                    │  [Verify]      │
│  ● LIVE CHECK      │                │
│                    │  STATUS        │
│                    │  Waiting...    │
└────────────────────┴────────────────┘
```

---

## 8. アニメーション・インタラクション

### 8-1. 遷移

```css
:root {
    --transition-fast: 0.12s ease;
    --transition-base: 0.18s ease;
    --transition-slow: 0.28s ease;
}
```

### 8-2. LEDアニメーション（ライブ表示）

```css
@keyframes led-pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.45; }
}
.led--active {
    animation: led-pulse 2s ease-in-out infinite;
}
```

### 8-3. カメラオブジェクト検出時のフィードバック

オブジェクト状態が `matched` に変わった瞬間：
```css
@keyframes frame-lock {
    0%   { border-color: var(--accent-dim); }
    40%  { border-color: var(--accent-bright); box-shadow: 0 0 20px var(--glow-accent); }
    100% { border-color: var(--accent); }
}
.camera-frame.matched {
    animation: frame-lock 0.6s ease-out forwards;
}
```

### 8-4. トースト通知の改善

状態に応じて色分け：

```css
.toast--success { border-left: 3px solid var(--status-ready); }
.toast--error   { border-left: 3px solid var(--status-alert); }
.toast--info    { border-left: 3px solid var(--accent); }
```

---

## 9. レスポンシブ対応

```css
/* Breakpoints */
@media (max-width: 900px) {
    .layout-grid { grid-template-columns: 1fr; }
    .status-grid { grid-template-columns: repeat(2, 1fr); }
    .topbar { flex-direction: column; align-items: flex-start; gap: 14px; }
}
@media (max-width: 480px) {
    .status-grid { grid-template-columns: 1fr 1fr; }
    .nav { gap: 0; }
    .nav a { padding: 8px 10px; font-size: 12px; }
}
```

---

## 10. ロゴ使用ガイドライン

| 場所 | サイズ | 処理 |
|------|--------|------|
| トップバー | 32–36px | `opacity: 0.9`, `drop-shadow` グロー |
| UI Lock 画面 | 64px | 中央配置、スキャン中はフェードパルス |
| ブラウザ favicon | 32px | PNG 切り出し |
| カメラフィード透かし | 要検討 | ウォーターマーク表示 |

---

## 11. 実装優先順位

| フェーズ | 対象 | 工数目安 |
|---------|------|---------|
| **Phase 1** | `base.html` CSS変数・ベーススタイル全面置換 | 半日 |
| **Phase 2** | `_components.html` マクロ更新（camera_frame, status_card, badge） | 2時間 |
| **Phase 3** | `home.html` + `store.html` + `retrieve.html` 適用 | 半日 |
| **Phase 4** | `maintenance.html` + `entry_management.html` 適用 | 2時間 |
| **Phase 5** | `emergency.html` + `ui_lock.html` 適用 | 2時間 |
| **Phase 6** | ロゴ画像の topbar 統合 + favicon 設定 | 1時間 |
| **Phase 7** | アニメーション・マイクロインタラクション | 2時間 |

---

## 12. 採用しないもの

| 候補 | 採用しない理由 |
|------|-------------|
| 外部CSSフレームワーク（Tailwind等） | CSP要件、オフライン動作要件 |
| アニメーション多用 | フィールド用途での集中の妨げ |
| 明るいカラーテーマ | ブランドアイデンティティとの不一致、夜間使用への配慮 |
| 複雑なグラデーション | コントラスト・視認性の劣化 |
| SVGアイコンライブラリ | 外部依存、CSP複雑化 |

---

## 付録：カラースウォッチ早見表

```
Background  ████ #070c09   ████ #0b1210   ████ #101a12   ████ #162018
Text        ████ #c8d8b0   ████ #849870   ████ #4e6244
Accent      ████ #7aaa48   ████ #4a7028   ████ #b0dc68
Status      ████ #50cc84   ████ #c89c36   ████ #cc4040   ████ #3a4e38
```
