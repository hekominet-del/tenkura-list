// 山の天気まとめ - service worker
// 方針: アプリ本体はキャッシュ優先、data.json はネットワーク優先（失敗時はキャッシュ）
const CACHE = 'tenkura-v4';  // 画面を更新したら必ず上げる（キャッシュ優先のため）
const SHELL = ['./', './index.html', './manifest.webmanifest',
  './icon-192.png', './icon-512.png', './icon-maskable-512.png', './apple-touch-icon.png',
  './img/mnt1.gif', './img/mnt2.gif', './img/mnt3.gif'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  if (url.pathname.endsWith('/data.json')) {
    // ネットワーク優先。オフラインなら最後に取れたデータ
    e.respondWith(
      fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put('./data.json', copy));
        return r;
      }).catch(() => caches.match('./data.json'))
    );
    return;
  }

  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
});
