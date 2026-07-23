# Instagram 自動投稿パイプライン（ひばの森 / ヒバ総研）

`posts-scheduled.json` に投稿を登録しておくと、GitHub Actions が毎日 JST 19:00 に
チェックし、公開時刻を過ぎて `status: "approved"` になっている投稿を
Instagram Graph API 経由で自動公開します。

## 仕組み

```
posts-scheduled.json に投稿を追加（status: "draft" or "approved"）
        ↓
毎日19:00 (JST) に GitHub Actions が起動
        ↓
publish_at を過ぎていて status:"approved" の投稿を抽出
        ↓
Graph API: POST /{ig-user-id}/media → POST /{ig-user-id}/media_publish
        ↓
成功したら status を "published" に書き換えてコミット
失敗したら status を "error" にして error_message を記録（自動リトライはしない）
```

画像は `images/` 以下に置いたものを
`https://raw.githubusercontent.com/gk21603-sys/Instagram/main/images/...`
として直接参照します（このリポジトリが public であることが前提）。

## 投稿の追加方法

`posts-scheduled.json` に以下の形式でオブジェクトを追加してください。

```json
{
  "account": "hibanomori",
  "publish_at": "2026-08-04T19:00:00+09:00",
  "type": "image",
  "pillar": "A",
  "images": ["images/2026-08/hiba-oil-01.jpg"],
  "caption": "国有林の青森ヒバ。\n専属職人の手で、一滴ずつ蒸留しています。",
  "hashtags": ["#青森ヒバ", "#青森ヒバ精油", "#ひばの森"],
  "status": "draft"
}
```

| フィールド | 内容 |
|---|---|
| `account` | `hibanomori`（ひばの森）または `hibasoken`（ヒバ総研） |
| `publish_at` | 公開したい日時（ISO8601、`+09:00` で JST 指定） |
| `type` | `image`（1枚 or 複数枚でカルーセル）/ `carousel` / `reel` |
| `pillar` | 戦略上のコンテンツ柱（A〜E、任意の記録用） |
| `images` | リポジトリ内の画像パスの配列。先に `images/` 配下にpushしておくこと |
| `caption` | 本文 |
| `hashtags` | ハッシュタグの配列（caption の後ろに自動で連結される） |
| `status` | `draft`（下書き・配信対象外）→ 確認後 `approved` に変更 → 自動で `published` / `error` になる |

**`status` を `"approved"` にするまでは絶対に配信されません。** ドラフトを置いておいて、
内容を確認してから `approved` に書き換えて push するのが唯一の「確定」操作です。

## 手動テスト

Actions タブ → 「Publish scheduled Instagram posts」→ 「Run workflow」で
cron を待たずにその場で実行できます。`publish_at` を過去の日時にした
`status: "approved"` のテスト投稿を1件だけ用意して試すのが安全です。

## Secrets（Settings → Secrets and variables → Actions に登録済み）

- `META_ACCESS_TOKEN` — システムユーザーの長期アクセストークン（60日）
- `IG_USER_ID_HIBANOMORI` — ひばの森の Instagram Business Account ID
- `IG_USER_ID_HIBASOKEN` — ヒバ総研の Instagram Business Account ID

`META_ACCESS_TOKEN` は60日で失効します。期限が近づいたら Meta Business Suite の
システムユーザー（`auto-poster`）画面から再発行し、Secrets を更新してください。

## 制約

- ストーリーズは Graph API 非対応のため自動化できません（手動 or Business Suite予約）
- 24時間あたり50投稿までの上限があるが、週3〜4本の運用では問題にならない
- リール（動画）は処理完了まで最大2分ポーリングして待機します
