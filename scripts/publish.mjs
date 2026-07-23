// scripts/publish.mjs
//
// posts-scheduled.json を読み、公開時刻を過ぎた status:"approved" の投稿を
// Instagram Graph API 経由で公開する。GitHub Actions から実行される想定。
//
// 画像URLは raw.githubusercontent.com 経由でこのリポジトリの images/ 以下を
// 直接参照する（リポジトリが public であることが前提）。

import { readFileSync, writeFileSync } from 'node:fs';

const GRAPH_VERSION = 'v21.0';
const DATA_PATH = 'posts-scheduled.json';

const TOKEN = process.env.META_ACCESS_TOKEN;
const IG_IDS = {
  hibanomori: process.env.IG_USER_ID_HIBANOMORI,
  hibasoken: process.env.IG_USER_ID_HIBASOKEN,
};

const REPO = process.env.GITHUB_REPOSITORY || 'gk21603-sys/Instagram';
const BRANCH = process.env.GITHUB_REF_NAME || 'main';
const IMAGE_BASE = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/`;

if (!TOKEN) {
  console.error('META_ACCESS_TOKEN が設定されていません。');
  process.exit(1);
}

function loadPosts() {
  const raw = readFileSync(DATA_PATH, 'utf-8');
  return JSON.parse(raw);
}

function savePosts(posts) {
  writeFileSync(DATA_PATH, JSON.stringify(posts, null, 2) + '\n');
}

async function graphPost(path, params) {
  const url = `https://graph.facebook.com/${GRAPH_VERSION}/${path}`;
  const body = new URLSearchParams({ ...params, access_token: TOKEN });
  const res = await fetch(url, { method: 'POST', body });
  const json = await res.json();
  if (!res.ok || json.error) {
    throw new Error(`Graph API error: ${JSON.stringify(json.error || json)}`);
  }
  return json;
}

async function graphGet(path, params) {
  const url = new URL(`https://graph.facebook.com/${GRAPH_VERSION}/${path}`);
  url.search = new URLSearchParams({ ...params, access_token: TOKEN }).toString();
  const res = await fetch(url);
  const json = await res.json();
  if (!res.ok || json.error) {
    throw new Error(`Graph API error: ${JSON.stringify(json.error || json)}`);
  }
  return json;
}

async function waitUntilFinished(containerId, timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const status = await graphGet(containerId, { fields: 'status_code' });
    if (status.status_code === 'FINISHED') return;
    if (status.status_code === 'ERROR') {
      throw new Error('メディアコンテナの処理が失敗しました (status_code: ERROR)');
    }
    await new Promise((r) => setTimeout(r, 5000));
  }
  throw new Error('メディアコンテナの処理がタイムアウトしました');
}

function buildCaption(post) {
  const hashtags = (post.hashtags || []).join(' ');
  return [post.caption, hashtags].filter(Boolean).join('\n\n');
}

async function publishPost(post) {
  const igUserId = IG_IDS[post.account];
  if (!igUserId) {
    throw new Error(`account "${post.account}" に対応するIG User IDが未設定です`);
  }

  const caption = buildCaption(post);

  // 単一画像
  if (post.type === 'image' && post.images.length === 1) {
    const container = await graphPost(`${igUserId}/media`, {
      image_url: IMAGE_BASE + post.images[0],
      caption,
    });
    await waitUntilFinished(container.id);
    const publish = await graphPost(`${igUserId}/media_publish`, {
      creation_id: container.id,
    });
    return publish.id;
  }

  // カルーセル（画像2枚以上 or type:"carousel"）
  if (post.type === 'carousel' || (post.type === 'image' && post.images.length > 1)) {
    const childIds = [];
    for (const img of post.images) {
      const child = await graphPost(`${igUserId}/media`, {
        image_url: IMAGE_BASE + img,
        is_carousel_item: 'true',
      });
      await waitUntilFinished(child.id);
      childIds.push(child.id);
    }
    const container = await graphPost(`${igUserId}/media`, {
      media_type: 'CAROUSEL',
      children: childIds.join(','),
      caption,
    });
    await waitUntilFinished(container.id);
    const publish = await graphPost(`${igUserId}/media_publish`, {
      creation_id: container.id,
    });
    return publish.id;
  }

  // リール（動画1本）
  if (post.type === 'reel') {
    const container = await graphPost(`${igUserId}/media`, {
      media_type: 'REELS',
      video_url: IMAGE_BASE + post.images[0],
      caption,
    });
    await waitUntilFinished(container.id);
    const publish = await graphPost(`${igUserId}/media_publish`, {
      creation_id: container.id,
    });
    return publish.id;
  }

  throw new Error(`未対応の type です: ${post.type}`);
}

async function main() {
  const posts = loadPosts();
  const now = new Date();
  let changed = false;

  for (const post of posts) {
    if (post.status !== 'approved') continue;

    const publishAt = new Date(post.publish_at);
    if (Number.isNaN(publishAt.getTime())) {
      console.error(`publish_at の形式が不正です: ${post.publish_at}`);
      continue;
    }
    if (publishAt > now) continue; // まだ時間になっていない

    console.log(`公開処理開始: account=${post.account} publish_at=${post.publish_at}`);
    try {
      const mediaId = await publishPost(post);
      post.status = 'published';
      post.published_media_id = mediaId;
      post.published_at = now.toISOString();
      changed = true;
      console.log(`  -> 成功: media_id=${mediaId}`);
    } catch (err) {
      post.status = 'error';
      post.error_message = String(err.message || err);
      changed = true;
      console.error(`  -> 失敗: ${post.error_message}`);
    }
  }

  if (changed) {
    savePosts(posts);
    console.log('posts-scheduled.json を更新しました。');
  } else {
    console.log('本日公開対象の投稿はありませんでした。');
  }
}

main().catch((err) => {
  console.error('予期しないエラー:', err);
  process.exit(1);
});
