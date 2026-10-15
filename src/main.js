const { app, BrowserWindow, ipcMain, protocol, net, shell, dialog, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');

const isDev = !app.isPackaged;

function userDir(name) {
  const base = app.getPath('userData');
  const p = path.join(base, name);
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
  return p;
}

const AUDIO_DIR = userDir('audio');
const BUNDLED_AUDIO_DIR = path.join(__dirname, 'assets', 'audio');
const COVER_DIR = userDir('covers');
const STORE_FILE = path.join(app.getPath('userData'), 'store.json');

let store = { favorites: [], history: [], volume: 0.8, lastTrackId: null, cached: {} };
try {
  if (fs.existsSync(STORE_FILE)) {
    store = Object.assign(store, JSON.parse(fs.readFileSync(STORE_FILE, 'utf8')));
  }
} catch (e) { /* ignore */ }
function saveStore() {
  try { fs.writeFileSync(STORE_FILE, JSON.stringify(store, null, 2), 'utf8'); } catch (e) { }
}

let library = null;
function loadLibrary() {
  if (library) return library;
  const p = path.join(__dirname, 'data', 'library.json');
  library = JSON.parse(fs.readFileSync(p, 'utf8'));
  return library;
}

// ---------------- B 站音源运行时重解析（兜底） ----------------
const BILI_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

function httpGetJson(url, headers, timeout = 20000) {
  return new Promise((resolve, reject) => {
    const req = net.request({ url, headers, redirect: 'follow' });
    let body = '';
    const t = setTimeout(() => { try { req.abort(); } catch (e) { } reject(new Error('timeout')); }, timeout);
    req.on('response', (res) => {
      res.on('data', (c) => { body += c.toString(); });
      res.on('end', () => { clearTimeout(t); try { resolve(JSON.parse(body)); } catch (e) { reject(e); } });
    });
    req.on('error', (e) => { clearTimeout(t); reject(e); });
    req.end();
  });
}

let buvid3 = '';
async function getBuvid() {
  if (buvid3) return buvid3;
  try {
    const j = await httpGetJson('https://api.bilibili.com/x/frontend/finger/spi', {
      'User-Agent': BILI_UA, 'Referer': 'https://www.bilibili.com/'
    });
    buvid3 = j && j.data && j.data.b_3 || '';
  } catch (e) { }
  return buvid3;
}

async function biliResolveUrl(bvid) {
  const cookie = 'buvid3=' + await getBuvid();
  const base = { 'User-Agent': BILI_UA, 'Referer': 'https://www.bilibili.com/', Cookie: cookie };
  const v = await httpGetJson(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`, base);
  if (!v || v.code !== 0) throw new Error('B站接口: ' + (v && v.message));
  const cid = v.data.cid;
  const p = await httpGetJson(
    `https://api.bilibili.com/x/player/playurl?bvid=${bvid}&cid=${cid}&qn=16&fnval=16&fourk=1&otype=json`, base);
  if (!p || p.code !== 0) throw new Error('B站取流: ' + (p && p.message));
  const d = p.data;
  if (d.dash && d.dash.audio && d.dash.audio.length) {
    const best = d.dash.audio.reduce((a, b) => (b.bandwidth > a.bandwidth ? b : a));
    return best.baseUrl || best.base_url;
  }
  if (d.durl && d.durl.length) return d.durl[0].url;
  throw new Error('无音频流');
}

// ---------------- 自定义协议：为本地缓存音频提供 Range 支持 ----------------
const AUDIO_SCHEME = 'buyiaudio';
protocol.registerSchemesAsPrivileged([
  {
    scheme: AUDIO_SCHEME,
    privileges: { bypassCSP: true, stream: true, supportFetchAPI: true, secure: true }
  }
]);

const MIME = {
  '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.flac': 'audio/flac',
  '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.aac': 'audio/aac', '.mp4': 'audio/mp4'
};

function resolveAudioFile(id) {
  if (!id) return null;
  const safe = String(id).replace(/[^a-zA-Z0-9_.-]/g, '');
  for (const dir of [AUDIO_DIR, BUNDLED_AUDIO_DIR]) {
    let files = [];
    try { files = fs.existsSync(dir) ? fs.readdirSync(dir) : []; } catch (e) { }
    const hit = files.find(f => f === safe || f.startsWith(safe + '.'));
    if (hit) return path.join(dir, hit);
  }
  return null;
}

function registerAudioProtocol() {
  protocol.registerStreamProtocol(AUDIO_SCHEME, (request, callback) => {
    try {
      const u = new URL(request.url);
      const id = decodeURIComponent(u.pathname.replace(/^\/+/, ''));
      const file = resolveAudioFile(id);
      if (!file) {
        callback({ statusCode: 404, headers: { 'Content-Type': 'text/plain' }, data: null });
        return;
      }
      const stat = fs.statSync(file);
      const ext = path.extname(file).toLowerCase();
      const type = MIME[ext] || 'application/octet-stream';
      const rangeHeader = (request.headers && (request.headers.Range || request.headers.range)) || '';
      const m = /bytes=(\d*)-(\d*)/.exec(rangeHeader);
      if (m) {
        const start = m[1] ? parseInt(m[1], 10) : 0;
        const end = m[2] ? parseInt(m[2], 10) : stat.size - 1;
        const chunk = Math.min(end, stat.size - 1) - start + 1;
        const stream = fs.createReadStream(file, { start, end: Math.min(end, stat.size - 1) });
        callback({
          statusCode: 206,
          headers: {
            'Content-Type': type,
            'Content-Length': String(chunk),
            'Accept-Ranges': 'bytes',
            'Content-Range': `bytes ${start}-${Math.min(end, stat.size - 1)}/${stat.size}`
          },
          data: stream
        });
        return;
      }
      callback({
        statusCode: 200,
        headers: {
          'Content-Type': type,
          'Content-Length': String(stat.size),
          'Accept-Ranges': 'bytes'
        },
        data: fs.createReadStream(file)
      });
    } catch (e) {
      callback({ statusCode: 500, headers: { 'Content-Type': 'text/plain' }, data: null });
    }
  });
}

// ---------------- 下载 ----------------
function extFromUrl(url) {
  const clean = url.split('?')[0];
  const ext = path.extname(clean).toLowerCase();
  if (['.mp3', '.m4a', '.flac', '.wav', '.ogg', '.aac', '.mp4'].includes(ext)) return ext;
  return '.mp3';
}

function downloadTrack(track) {
  return new Promise((resolve) => {
    const ext = extFromUrl(track.url || '');
    const target = path.join(AUDIO_DIR, `${track.id}${ext}`);
    if (fs.existsSync(target) && fs.statSync(target).size > 20000) {
      resolve({ ok: true, file: target, cached: true });
      return;
    }
    const isBili = (track.url || '').includes('bilivideo.com') || (track.url || '').includes('hdslb');
    const headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    };
    if (isBili) {
      headers['Referer'] = 'https://www.bilibili.com/';
      headers['Origin'] = 'https://www.bilibili.com';
    }
    let req;
    try {
      req = net.request({ url: track.url, headers, redirect: 'follow' });
    } catch (e) {
      resolve({ ok: false, error: String(e) });
      return;
    }
    let received = 0;
    const tmp = target + '.part';
    const ws = fs.createWriteStream(tmp);
    let settled = false;
    const fail = (msg) => {
      if (settled) return; settled = true;
      try { ws.close(); } catch (e) { }
      try { if (fs.existsSync(tmp)) fs.unlinkSync(tmp); } catch (e) { }
      resolve({ ok: false, error: msg });
    };
    req.on('response', (res) => {
      const code = res.statusCode;
      if (code >= 400) { fail('HTTP ' + code); return; }
      const total = parseInt(res.headers['content-length'] || '0', 10);
      res.on('data', (chunk) => {
        received += chunk.length;
        ws.write(chunk);
        if (total) {
          sendProgress(track.id, Math.min(99, Math.floor(received / total * 100)));
        }
      });
      res.on('end', () => {
        ws.end(() => {
          if (received < 20000) { fail('文件过小，音源可能已失效'); return; }
          try {
            if (fs.existsSync(target)) fs.unlinkSync(target);
            fs.renameSync(tmp, target);
          } catch (e) { fail(String(e)); return; }
          if (settled) return; settled = true;
          store.cached[track.id] = { file: target, size: received, at: Date.now() };
          saveStore();
          sendProgress(track.id, 100);
          resolve({ ok: true, file: target });
        });
      });
      res.on('error', () => fail('网络错误'));
    });
    req.on('error', (e) => fail(String(e && e.message || e)));
    setTimeout(() => { if (!settled) { try { req.abort(); } catch (e) { } fail('下载超时'); } }, 180000);
    req.end();
  });
}

function sendProgress(id, p) {
  const wins = BrowserWindow.getAllWindows();
  wins.forEach(w => w.webContents.send('download-progress', { id, progress: p }));
}

// ---------------- 窗口 ----------------
let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#F4EFE6',
    show: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false
    }
  });

  Menu.setApplicationMenu(null);
  if (process.env.BUYI_DEBUG) {
    mainWindow.webContents.on('console-message', (e, level, message, line, sourceId) => {
      console.log('[renderer][' + level + ']', message, sourceId + ':' + line);
    });
    mainWindow.webContents.on('did-fail-load', (e, code, desc) => {
      console.log('[load-fail]', code, desc);
    });
  }
  const testplay = process.argv.includes('--testplay');
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'),
    testplay ? { search: '?testplay=1' } : undefined);
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (process.env.BUYI_SHOT) {
      setTimeout(async () => {
        try {
          const img = await mainWindow.webContents.capturePage();
          fs.writeFileSync(process.env.BUYI_SHOT, img.toPNG());
          console.log('[shot] saved', process.env.BUYI_SHOT);
        } catch (e) { console.log('[shot] fail', e.message); }
      }, 3000);
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  if (process.env.BUYI_DEBUG) {
    try {
      const files = fs.existsSync(BUNDLED_AUDIO_DIR) ? fs.readdirSync(BUNDLED_AUDIO_DIR) : [];
      console.log('[debug] bundled audio:', files.length, BUNDLED_AUDIO_DIR);
    } catch (e) {
      console.log('[debug] bundled audio error:', e.message);
    }
  }
  registerAudioProtocol();
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// ---------------- IPC ----------------
ipcMain.handle('get-library', async () => {
  const lib = loadLibrary();
  const cachedIds = {};
  [AUDIO_DIR, BUNDLED_AUDIO_DIR].forEach((dir) => {
    try {
      fs.readdirSync(dir).forEach(f => { cachedIds[f.split('.')[0]] = true; });
    } catch (e) { }
  });
  return {
    meta: lib.meta,
    tracks: lib.tracks.map(t => ({ ...t, cached: !!cachedIds[t.id] })),
    store: { favorites: store.favorites, history: store.history, volume: store.volume }
  };
});

ipcMain.handle('ensure-audio', async (e, id) => {
  const lib = loadLibrary();
  const track = lib.tracks.find(t => t.id === id);
  if (!track) return { ok: false, error: '曲目不存在' };
  const existing = resolveAudioFile(id);
  if (existing) return { ok: true, src: `${AUDIO_SCHEME}://media/${path.basename(existing)}` };
  if (!track.url) return { ok: false, error: '该曲目暂无可用音源' };
  let r = await downloadTrack(track);
  const bvid = track.bvid || (/^BV[0-9A-Za-z]{10}$/.test(track.album || '') ? track.album : '');
  if (!r.ok && track.source === 'B站' && bvid) {
    try {
      const u = await biliResolveUrl(bvid);
      if (u) {
        track.url = u;
        const saved = library.tracks.find(t => t.id === id);
        if (saved) saved.url = u;
        r = await downloadTrack({ ...track, url: u });
      }
    } catch (e2) {
      r = { ok: false, error: '音源重解析失败' };
    }
  }
  if (!r.ok) return r;
  return { ok: true, src: `${AUDIO_SCHEME}://media/${path.basename(r.file)}` };
});

ipcMain.handle('cache-track', async (e, id) => {
  const lib = loadLibrary();
  const track = lib.tracks.find(t => t.id === id);
  if (!track) return { ok: false, error: '曲目不存在' };
  if (resolveAudioFile(id)) return { ok: true, cached: true };
  return await downloadTrack(track);
});

ipcMain.handle('remove-cache', async (e, id) => {
  const f = resolveAudioFile(id);
  if (f) { try { fs.unlinkSync(f); } catch (e) { } }
  delete store.cached[id];
  saveStore();
  return { ok: true };
});

ipcMain.handle('save-store', async (e, patch) => {
  if (!patch) return { ok: false };
  if (patch.favorites) store.favorites = patch.favorites;
  if (patch.history) store.history = patch.history;
  if (typeof patch.volume === 'number') store.volume = patch.volume;
  if (patch.lastTrackId !== undefined) store.lastTrackId = patch.lastTrackId;
  saveStore();
  return { ok: true };
});

ipcMain.handle('open-cache-dir', async () => {
  shell.openPath(AUDIO_DIR);
  return { ok: true };
});

ipcMain.handle('cache-stats', async () => {
  let count = 0, size = 0;
  try {
    fs.readdirSync(AUDIO_DIR).forEach(f => {
      const st = fs.statSync(path.join(AUDIO_DIR, f));
      if (st.size > 20000) { count++; size += st.size; }
    });
  } catch (e) { }
  return { count, size };
});

ipcMain.handle('app-info', async () => ({
  version: app.getVersion(),
  electron: process.versions.electron,
  cacheDir: AUDIO_DIR
}));

// 窗口控制
ipcMain.on('win-min', () => mainWindow && mainWindow.minimize());
ipcMain.on('win-max', () => {
  if (!mainWindow) return;
  if (mainWindow.isMaximized()) mainWindow.unmaximize();
  else mainWindow.maximize();
});
ipcMain.on('win-close', () => mainWindow && mainWindow.close());
ipcMain.on('win-is-max', (e) => {
  e.returnValue = mainWindow ? mainWindow.isMaximized() : false;
});
