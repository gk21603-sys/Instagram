// scripts/collect_insights.mjs
//
// 公開済みの投稿（posts-scheduled.json の published_media_id）について
// Instagram Graph API のインサイトを取得し、insights/latest.json に記録する。
// 投稿の型・タグの組み合わせ（exp）と数字を突き合わせて、何が伸びるかを試行錯誤するための材料。
//
// - フィード（image / carousel）: 公開後45日分を毎回取り直す（数字は数日かけて伸びるため）
// - ストーリー: APIで取れるのは公開後24時間のみ。取れなくなったら最後の値を残す
// - アカウント: フォロワー数を日ごとに1点記録する

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';

const GRAPH = 'https://graph.facebook.com/v21.0';
const TOKEN = process.env.META_ACCESS_TOKEN;
const IG_IDS = {
  hibanomori: process.env.IG_USER_ID_HIBANOMORI,
  hibasoken: process.env.IG_USER_ID_HIBASOKEN,
};
const OUT_DIR = 'insights';
const OUT = `${OUT_DIR}/latest.json`;
const FEED_DAYS = 45;

const FEED_METRICS = ['reach', 'views', 'saved', 'shares', 'likes', 'comments', 'total_interactions', 'profile_visits', 'follows'];
let lastError = null;
const STORY_METRICS = ['reach', 'views', 'replies', 'shares', 'total_interactions', 'navigation'];

if (!TOKEN) {
  console.error('META_ACCESS_TOKEN が設定されていません。');
  process.exit(1);
}

async function get(path, params = {}) {
  const url = new URL(`${GRAPH}/${path}`);
  for (const [k, v] of Object.entries({ ...params, access_token: TOKEN })) url.searchParams.set(k, v);
  const res = await fetch(url);
  const json = await res.json();
  if (!res.ok || json.error) throw new Error(json.error?.message || `HTTP ${res.status}`);
  return json;
}

// 指標は1つずつ取る（未対応の指標が1つ混ざるとまとめて失敗するため）
async function mediaInsights(id, metrics) {
  const out = {};
  for (const m of metrics) {
    try {
      const j = await get(`${id}/insights`, { metric: m });
      const v = j.data?.[0]?.values?.[0]?.value ?? j.data?.[0]?.total_value?.value;
      if (v !== undefined) out[m] = v;
    } catch (e) {
      // 未対応・期限切れは飛ばす。権限不足などで全部落ちたときに気づけるよう最後のエラーは残す
      lastError = e.message;
    }
  }
  return out;
}

function load() {
  if (!existsSync(OUT)) return { media: {}, followers: {} };
  return JSON.parse(readFileSync(OUT, 'utf-8'));
}

async function main() {
  const posts = JSON.parse(readFileSync('posts-scheduled.json', 'utf-8'));
  const data = load();
  data.media ||= {};
  data.followers ||= {};
  const now = Date.now();
  let fetched = 0;

  for (const p of posts) {
    const id = p.published_media_id;
    if (!id || !p.published_at) continue;
    const ageDays = (now - Date.parse(p.published_at)) / 86400000;
    const isStory = p.type === 'story';
    if (isStory ? ageDays > 1.2 : ageDays > FEED_DAYS) continue;

    const metrics = await mediaInsights(id, isStory ? STORY_METRICS : FEED_METRICS);
    const prev = data.media[id] || {};
    data.media[id] = {
      account: p.account,
      date: p.publish_at.slice(0, 10),
      published_at: p.published_at,
      type: p.type,
      pillar: p.pillar,
      format: p.format || null,
      exp: p.exp || null,
      note_id: p.note_id || null,
      hashtags: p.hashtags || [],
      title: p.title || (p.caption || '').split('\n')[0].slice(0, 40),
      metrics: Object.keys(metrics).length ? metrics : prev.metrics || {},
      updated_at: Object.keys(metrics).length ? new Date().toISOString() : prev.updated_at || null,
    };
    fetched++;
  }

  const today = new Date(now + 9 * 3600000).toISOString().slice(0, 10); // JST
  for (const [acct, uid] of Object.entries(IG_IDS)) {
    if (!uid) continue;
    try {
      const j = await get(uid, { fields: 'followers_count,media_count' });
      data.followers[acct] ||= {};
      data.followers[acct][today] = j.followers_count;
    } catch (e) {
      console.error(`${acct}: フォロワー数の取得に失敗: ${e.message}`);
    }
  }

  data.fetched_at = new Date().toISOString();
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR);
  writeFileSync(OUT, JSON.stringify(data, null, 2) + '\n');
  const empty = Object.values(data.media).filter((m) => !Object.keys(m.metrics).length).length;
  console.log(`インサイト取得: ${fetched}件（数字が空のもの ${empty}件）`);
  if (fetched && empty === Object.keys(data.media).length) {
    console.error(`すべて取得できませんでした。トークンの権限（instagram_manage_insights）を確認してください。最後のエラー: ${lastError}`);
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
