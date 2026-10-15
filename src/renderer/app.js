/* 布依音 · 布依族民族音乐播放器 —— 渲染进程 */
(function () {
  'use strict';

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const api = window.buyi;

  const state = {
    tracks: [],
    meta: {},
    view: 'home',
    detail: null,        // { type:'playlist'|'search'|'fav'|'history'|'cache', id, title, desc, list }
    queue: [],           // 当前播放列表（track 对象数组）
    qi: -1,              // 当前索引
    playing: false,
    mode: 'loop',        // loop | single | shuffle
    volume: 0.8,
    muted: false,
    favorites: new Set(),
    history: [],
    searchTerm: '',
    progress: {}         // id -> 下载进度
  };

  const audio = new Audio();
  audio.preload = 'auto';
  audio.volume = state.volume;

  /* ---------------- 歌单定义 ---------------- */
  const PLAYLISTS = [
    { id: 'haohuahong', name: '好花红 · 布依名片', icon: '花', color: ['#8E2B26', '#C8362F'],
      desc: '「好花红」是布依族流传最广的民歌，源自贵州惠水，被称作布依族的音乐名片。这里收录了它的各个演唱版本与改编。',
      match: (t) => /好花红/.test(t.title) },
    { id: 'shange', name: '山歌悠悠 · 民谣', icon: '山', color: ['#16324B', '#2E6B8F'],
      desc: '布依族依山傍水而居，山歌、浪哨歌、盘歌是日常生活的一部分，即兴对唱，见物起兴。',
      match: (t) => t.category === '山歌民谣' },
    { id: 'qiyue', name: '勒尤与木叶 · 器乐', icon: '乐', color: ['#1E4463', '#3C7A6E'],
      desc: '勒尤是布依族特有的双簧吹管乐器，音色深沉悠远；木叶则以一片树叶吹奏出山野之音。',
      match: (t) => t.category === '器乐' },
    { id: 'tongyao', name: '娃娃的歌 · 童谣', icon: '娃', color: ['#3C5A78', '#7FA8C4'],
      desc: '布依族的摇篮曲与童谣，用最朴素的旋律把民族记忆交给下一代。',
      match: (t) => t.category === '童谣' },
    { id: 'jiuge', name: '喜事酒歌 · 婚俗', icon: '喜', color: ['#7A2E33', '#B4574C'],
      desc: '婚嫁、迎亲、拦门、敬酒，布依族的人生礼俗都伴随着成套的歌。',
      match: (t) => t.category === '婚俗酒歌' },
    { id: 'zhijin', name: '织布与蜡染 · 劳动', icon: '织', color: ['#2A2A48', '#6B4A72'],
      desc: '织锦、蜡染、挑花、耕作栽秧——布依人在劳作中唱出的歌，纹样与旋律一样细密。',
      match: (t) => t.category === '劳动生活' },
    { id: 'xinsheng', name: '布依新声 · 改编', icon: '新', color: ['#123A4A', '#2F6F8C'],
      desc: '年轻一代用流行、说唱、电子的方式重新演绎布依旋律，是古老山歌的当代表达。',
      match: (t) => t.category === '新创改编' },
    { id: 'wudao', name: '载歌载舞 · 舞蹈音乐', icon: '舞', color: ['#4A3A6B', '#8A6BA8'],
      desc: '糠包舞、竹竿舞、金钱棍、竹鼓舞——布依族的节庆与民俗总在鼓点与舞步里展开。',
      match: (t) => t.category === '舞蹈' }
  ];

  const CULTURE = [
    { t: '布依族', p: '布依族主要聚居在贵州黔南、黔西南及安顺、贵阳一带，人口约三百余万。语言属汉藏语系壮侗语族，历史上被称为「仲家」「夷家」，1953 年统一称为布依族。布依村寨多依山傍水，石板房、吊脚楼错落有致。' ,
      tags: ['贵州黔南', '黔西南', '壮侗语族', '石板房'] },
    { t: '《好花红》', p: '出自贵州惠水的布依族民歌，上世纪五十年代被整理改编后传遍全国，成为布依族最具代表性的音乐符号。歌词以刺梨花起兴，借花喻情，曲调明快悠扬。' ,
      tags: ['惠水', '民歌中国', '刺梨花'] },
    { t: '勒尤与木叶', p: '勒尤是布依族独有的双簧吹管乐器，音色低沉缠绵，常用于青年「浪哨」（谈情说爱）时传情；木叶则以一片树叶贴唇吹奏，技艺高超者可吹出完整曲调。此外还有铜鼓、姊妹箫、唢呐、月琴等。' ,
      tags: ['勒尤', '木叶', '铜鼓', '姊妹箫'] },
    { t: '蜡染与织锦', p: '布依族蜡染以靛蓝与白为主色，纹样多取铜鼓纹、水波纹、蕨菜纹与几何回纹；织锦则用经纬交织出细密的菱形与花鸟图案，常用于被面、背带与服饰。' ,
      tags: ['靛蓝', '铜鼓纹', '水波纹', '织锦'] },
    { t: '歌节与节俗', p: '三月三、六月六是布依族最重要的传统歌节，此外还有兴义查白歌节。节日期间青年男女对歌、浪哨、丢花包，山歌此起彼伏，通宵不绝。' ,
      tags: ['三月三', '六月六', '查白歌节'] },
    { t: '关于本曲库', p: '本曲库共收录布依族相关曲目数百首，来源涵盖酷我音乐、咪咕音乐、B 站与微信音频等公开渠道，仅用于民族音乐的欣赏、学习与保护性传播。' ,
      tags: ['民族音乐', '数字保护'] }
  ];

  /* ---------------- 工具 ---------------- */
  function fmtTime(s) {
    if (!isFinite(s) || s < 0) s = 0;
    const m = Math.floor(s / 60);
    const ss = Math.floor(s % 60);
    return String(m).padStart(2, '0') + ':' + String(ss).padStart(2, '0');
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }
  let toastTimer = null;
  function toast(msg) {
    const el = $('#toast');
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2200);
  }
  const PLACEHOLDER = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">` +
    `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">` +
    `<stop offset="0%" stop-color="#16324B"/><stop offset="100%" stop-color="#2E6B8F"/>` +
    `</linearGradient></defs><rect width="300" height="300" fill="url(#g)"/>` +
    `<circle cx="150" cy="150" r="86" fill="none" stroke="#C9A227" stroke-width="4" opacity=".8"/>` +
    `<circle cx="150" cy="150" r="56" fill="none" stroke="#C9A227" stroke-width="2.5" opacity=".55"/>` +
    `<circle cx="150" cy="150" r="22" fill="#C8362F"/>` +
    `<g stroke="#F7F2E8" stroke-width="5" stroke-linecap="round" opacity=".85">` +
    `<line x1="150" y1="34" x2="150" y2="60"/><line x1="150" y1="240" x2="150" y2="266"/>` +
    `<line x1="34" y1="150" x2="60" y2="150"/><line x1="240" y1="150" x2="266" y2="150"/>` +
    `<line x1="66" y1="66" x2="84" y2="84"/><line x1="216" y1="216" x2="234" y2="234"/>` +
    `<line x1="66" y1="234" x2="84" y2="216"/><line x1="216" y1="84" x2="234" y2="66"/>` +
    `</g></svg>`);
  function coverPath(p) { return p ? '../' + p : PLACEHOLDER; }

  /* ---------------- 初始化 ---------------- */
  async function init() {
    const data = await api.getLibrary();
    state.tracks = data.tracks;
    state.meta = data.meta;
    state.favorites = new Set(data.store.favorites || []);
    state.history = data.store.history || [];
    state.volume = typeof data.store.volume === 'number' ? data.store.volume : 0.8;
    audio.volume = state.volume;
    $('#volFill').style.width = (state.volume * 100) + '%';

    buildPlaylistNav();
    renderHero();
    renderDaily();
    renderPlaylists();
    renderHomeTracks();
    renderCulture();
    updateSideStat();
    bindEvents();
    // 测试通道：--testplay 自动播放并打开播放页
    if (new URLSearchParams(location.search).get('testplay')) {
      setTimeout(async () => {
        const cached = state.tracks.filter((t) => t.playable && t.cached);
        console.log('[TEST] cached=' + cached.length +
          ' first=' + (cached[0] ? cached[0].id + '/' + cached[0].title.slice(0, 12) : 'none'));
        await playList(cached.length ? cached : state.tracks.filter((t) => t.playable), 0, true);
        openPlayerPage();
        setTimeout(() => {
          console.log('[TEST] playing=' + state.playing + ' time=' + audio.currentTime.toFixed(1) +
            ' title=' + (state.current && state.current.title.slice(0, 20)));
        }, 6000);
      }, 1200);
    }
    api.onProgress(({ id, progress }) => {
      state.progress[id] = progress;
      if (state.current && state.current.id === id) {
        if (progress < 100) $('#pbArtist').textContent = '正在缓冲音源 ' + progress + '%';
      }
      refreshRowStates();
    });
  }

  /* ---------------- 侧边栏歌单 ---------------- */
  function buildPlaylistNav() {
    const box = $('#playlistNav');
    box.innerHTML = PLAYLISTS.map((p) => {
      const n = state.tracks.filter(p.match).length;
      return `<a class="side-item" data-pl="${p.id}"><span style="width:18px;text-align:center;color:var(--red);font-weight:700">${p.icon}</span><span>${p.name.split(' · ')[0]}</span><span class="badge">${n}</span></a>`;
    }).join('');
    box.querySelectorAll('[data-pl]').forEach((el) => {
      el.onclick = () => openPlaylist(el.dataset.pl);
    });
  }

  function updateSideStat() {
    const total = state.tracks.length;
    const ok = state.tracks.filter((t) => t.playable).length;
    const cached = state.tracks.filter((t) => t.cached).length;
    $('#sideStat').innerHTML =
      `曲库 ${total} 首 · 可播放 ${ok} 首<br>已缓存 ${cached} 首<br><span style="color:var(--indigo-500)">${esc(state.meta.group || '布依族')}民族音乐</span>`;
  }

  /* ---------------- Hero ---------------- */
  const HERO = [
    { title: '好花红 · 布依族的声音名片',
      text: '「好花红来好花红，好花生在刺梨蓬。」源自贵州惠水的布依族民歌，唱遍了南北盘江两岸的村寨。这里收录了它的各个版本。',
      g1: '#0E2436', g2: '#2E6B8F', art: 'drum' },
    { title: '勒尤 · 木叶 · 铜鼓',
      text: '一片树叶可以吹出一座山的回响，一支勒尤能说出说不出口的话。布依族的器乐，藏在山野与节庆之间。',
      g1: '#123A4A', g2: '#3C7A6E', art: 'leaf' },
    { title: '靛蓝与白 · 蜡染上的歌',
      text: '靛蓝染出的布，铜鼓纹、水波纹、蕨菜纹层层叠叠。布依人把山歌的节奏，织进了衣裳与被面。',
      g1: '#2A2A48', g2: '#6B4A72', art: 'batik' }
  ];

  function heroArt(kind) {
    if (kind === 'drum') {
      return `<svg width="150" height="150" viewBox="0 0 200 200">
        <g fill="none" stroke="#C9A227" stroke-opacity=".85">
          <circle cx="100" cy="100" r="88" stroke-width="3"/>
          <circle cx="100" cy="100" r="62" stroke-width="2"/>
          <circle cx="100" cy="100" r="26" stroke-width="3"/>
        </g>
        <circle cx="100" cy="100" r="12" fill="#C8362F"/>
        <g stroke="#F7F2E8" stroke-opacity=".8" stroke-width="4" stroke-linecap="round">
          <line x1="100" y1="6" x2="100" y2="30"/><line x1="100" y1="170" x2="100" y2="194"/>
          <line x1="6" y1="100" x2="30" y2="100"/><line x1="170" y1="100" x2="194" y2="100"/>
          <line x1="33" y1="33" x2="50" y2="50"/><line x1="150" y1="150" x2="167" y2="167"/>
          <line x1="33" y1="167" x2="50" y2="150"/><line x1="150" y1="50" x2="167" y2="33"/>
        </g></svg>`;
    }
    if (kind === 'leaf') {
      return `<svg width="150" height="150" viewBox="0 0 200 200">
        <path d="M100 20 C40 60 30 130 100 185 C170 130 160 60 100 20Z" fill="none" stroke="#8FC0A9" stroke-width="3"/>
        <path d="M100 25 V180" stroke="#F7F2E8" stroke-opacity=".7" stroke-width="2"/>
        <g stroke="#C9A227" stroke-opacity=".6" stroke-width="1.6">
          <path d="M100 60 L58 78"/><path d="M100 60 L142 78"/>
          <path d="M100 100 L52 122"/><path d="M100 100 L148 122"/>
          <path d="M100 140 L62 158"/><path d="M100 140 L138 158"/>
        </g></svg>`;
    }
    return `<svg width="150" height="150" viewBox="0 0 200 200">
      <rect x="20" y="20" width="160" height="160" rx="8" fill="none" stroke="#F7F2E8" stroke-opacity=".7" stroke-width="3"/>
      <g stroke="#7FA8C4" stroke-width="3" opacity=".9">
        <path d="M20 60 q20 -24 40 0 t40 0 t40 0 t40 0"/>
        <path d="M20 100 q20 -24 40 0 t40 0 t40 0 t40 0"/>
        <path d="M20 140 q20 -24 40 0 t40 0 t40 0 t40 0"/>
      </g>
      <g fill="none" stroke="#C8362F" stroke-width="3">
        <rect x="76" y="76" width="48" height="48" transform="rotate(45 100 100)"/>
      </g></svg>`;
  }

  let heroIdx = 0, heroTimer = null;
  function renderHero() {
    const el = $('#hero');
    el.innerHTML = HERO.map((h, i) => `
      <div class="hero-slide ${i === 0 ? 'on' : ''}" style="background:linear-gradient(110deg,${h.g1},${h.g2})">
        <div class="hs-art">${heroArt(h.art)}</div>
        <div><h3>${h.title}</h3><p>${h.text}</p></div>
      </div>`).join('') +
      `<div class="hero-dots">${HERO.map((_, i) => `<i class="${i === 0 ? 'on' : ''}" data-i="${i}"></i>`).join('')}</div>`;
    el.querySelectorAll('.hero-dots i').forEach((d) => {
      d.onclick = () => { heroIdx = +d.dataset.i; showHero(); };
    });
    clearInterval(heroTimer);
    heroTimer = setInterval(() => { heroIdx = (heroIdx + 1) % HERO.length; showHero(); }, 6000);
  }
  function showHero() {
    $$('.hero-slide').forEach((s, i) => s.classList.toggle('on', i === heroIdx));
    $$('.hero-dots i').forEach((d, i) => d.classList.toggle('on', i === heroIdx));
  }

  /* ---------------- 每日推荐 ---------------- */
  function pickDaily(n) {
    const pool = state.tracks.filter((t) => t.playable);
    const rest = state.tracks.filter((t) => !t.playable);
    const arr = pool.slice();
    // 以日期为种子做一次稳定洗牌
    const seed = new Date().getFullYear() * 10000 + (new Date().getMonth() + 1) * 100 + new Date().getDate();
    let s = seed;
    for (let i = arr.length - 1; i > 0; i--) {
      s = (s * 9301 + 49297) % 233280;
      const j = Math.floor((s / 233280) * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr.concat(rest).slice(0, n);
  }

  function renderDaily() {
    const list = pickDaily(10);
    $('#dailyGrid').innerHTML = list.map(cardHtml).join('');
    bindCards($('#dailyGrid'));
  }
  function cardHtml(t) {
    return `<div class="mcard" data-id="${t.id}">
      <div class="cov">
        <img src="${coverPath(t.cover)}" loading="lazy" alt="">
        <div class="mask"><svg><use href="#i-play"/></svg></div>
      </div>
      <div class="ttl">${esc(t.title)}</div>
      <div class="sub">${esc(t.artist)} · ${t.durationText}</div>
    </div>`;
  }
  function bindCards(root) {
    root.querySelectorAll('.mcard').forEach((el) => {
      el.onclick = () => {
        const t = byId(el.dataset.id);
        if (!t) return;
        const list = $('#dailyGrid').querySelectorAll('.mcard');
        playList(Array.from(list).map((n) => byId(n.dataset.id)), Array.from(list).indexOf(el));
      };
    });
  }

  /* ---------------- 歌单卡 ---------------- */
  function renderPlaylists() {
    $('#plGrid').innerHTML = PLAYLISTS.map((p) => {
      const n = state.tracks.filter(p.match).length;
      return `<div class="plcard" data-pl="${p.id}">
        <div class="pc" style="background:linear-gradient(135deg,${p.color[0]},${p.color[1]})">${p.icon}</div>
        <div class="pi"><b>${esc(p.name)}</b><span>${n} 首 · 布依族</span></div>
      </div>`;
    }).join('');
    $('#plGrid').querySelectorAll('[data-pl]').forEach((el) => {
      el.onclick = () => openPlaylist(el.dataset.pl);
    });
  }

  function renderHomeTracks() {
    const list = state.tracks.filter((t) => t.playable).slice(0, 20);
    renderTable($('#homeTracks'), list, false);
  }

  /* ---------------- 曲目表 ---------------- */
  function renderTable(root, list, showIndex) {
    if (!list.length) {
      root.innerHTML = `<div class="empty"><b>♪</b>这里还没有歌曲</div>`;
      return;
    }
    root.innerHTML =
      `<div class="tt-head">
        <div style="text-align:center">#</div><div>歌曲</div><div>歌手</div><div>专辑</div>
        <div>时长</div><div style="text-align:right">操作</div>
      </div>` +
      list.map((t, i) => rowHtml(t, i)).join('');
    bindRows(root, list);
  }

  function rowHtml(t, i) {
    const cur = state.current && state.current.id === t.id;
    const fav = state.favorites.has(t.id);
    const p = state.progress[t.id];
    const buffering = p != null && p < 100 && cur;
    return `<div class="tt-row ${cur ? 'playing' : ''} ${t.playable ? '' : 'disabled'}" data-id="${t.id}">
      <div class="c-idx">${cur ? '▶' : (i + 1)}</div>
      <div class="c-title"><span class="nm">${esc(t.title)}</span>
        ${t.playable ? '' : '<span class="tag warn">音源待修复</span>'}
        ${t.cached ? '<span class="tag">已缓存</span>' : ''}
        ${buffering ? `<span class="tag">缓冲 ${p}%</span>` : ''}
      </div>
      <div class="c-sub">${esc(t.artist)}</div>
      <div class="c-sub">${esc(t.album)}</div>
      <div class="c-time">${t.durationText}</div>
      <div class="c-ops">
        <button data-act="fav" class="${fav ? 'on' : ''}" title="喜欢"><svg><use href="#${fav ? 'i-heart-fill' : 'i-heart'}"/></svg></button>
        <button data-act="dl" title="缓存到本地"><svg><use href="#i-download"/></svg></button>
      </div>
    </div>`;
  }

  function bindRows(root, list) {
    root.querySelectorAll('.tt-row').forEach((el) => {
      const t = byId(el.dataset.id);
      el.ondblclick = () => playList(list, list.indexOf(t));
      el.querySelector('.c-title').onclick = () => playList(list, list.indexOf(t));
      const favBtn = el.querySelector('[data-act="fav"]');
      const dlBtn = el.querySelector('[data-act="dl"]');
      favBtn.onclick = (e) => { e.stopPropagation(); toggleFav(t); refreshRowStates(); };
      dlBtn.onclick = async (e) => {
        e.stopPropagation();
        if (!t.playable) { toast('该曲目暂无可用音源'); return; }
        toast('开始缓存：' + t.title.slice(0, 16));
        const r = await api.cacheTrack(t.id);
        if (r.ok) { t.cached = true; toast('已缓存到本地'); refreshRowStates(); updateSideStat(); }
        else toast('缓存失败：' + (r.error || '音源不可用'));
      };
    });
  }

  function refreshRowStates() {
    ['#homeTracks', '#detailTracks'].forEach((sel) => {
      const root = $(sel);
      root.querySelectorAll('.tt-row').forEach((el) => {
        const t = byId(el.dataset.id);
        if (!t) return;
        const cur = state.current && state.current.id === t.id;
        el.classList.toggle('playing', !!cur);
        el.classList.toggle('disabled', !t.playable);
        const idxEl = el.querySelector('.c-idx');
        if (idxEl && !cur) idxEl.textContent = Array.from(el.parentNode.children).indexOf(el);
        const ops = el.querySelector('.c-ops');
        if (ops) {
          ops.innerHTML =
            `<button data-act="fav" class="${state.favorites.has(t.id) ? 'on' : ''}" title="喜欢"><svg><use href="#${state.favorites.has(t.id) ? 'i-heart-fill' : 'i-heart'}"/></svg></button>
             <button data-act="dl" title="缓存到本地"><svg><use href="#i-download"/></svg></button>`;
        }
        const titleEl = el.querySelector('.c-title');
        if (titleEl) {
          const p = state.progress[t.id];
          const buffering = p != null && p < 100 && cur;
          titleEl.innerHTML = `<span class="nm">${esc(t.title)}</span>` +
            (t.playable ? '' : '<span class="tag warn">音源待修复</span>') +
            (t.cached ? '<span class="tag">已缓存</span>' : '') +
            (buffering ? `<span class="tag">缓冲 ${p}%</span>` : '');
        }
      });
    });
    if ($('#queuePanel').classList.contains('hidden') === false) renderQueue();
  }

  /* ---------------- 视图切换 ---------------- */
  function setView(name) {
    state.view = name;
    $$('.side-item').forEach((el) => el.classList.remove('active'));
    const nav = document.querySelector(`.side-item[data-view="${name}"]`);
    if (nav) nav.classList.add('active');
    $('#view-home').classList.toggle('hidden', name !== 'home');
    $('#view-culture').classList.toggle('hidden', name !== 'culture');
    $('#view-detail').classList.toggle('hidden', !(name === 'detail' || name === 'library' ||
      name === 'favorites' || name === 'history' || name === 'cache' || name === 'search'));
    $('#content').scrollTop = 0;
  }

  function showDetail(cfg) {
    state.detail = cfg;
    setView('detail');
    $('#detailHead').innerHTML = `
      <div class="dh-cov">${cfg.img ? `<img src="${cfg.img}">` : `<div class="dh-ph">${esc(cfg.icon || '布')}</div>`}</div>
      <div class="dh-info">
        <div class="kind">${esc(cfg.kind || '歌单')}</div>
        <h1>${esc(cfg.title)}</h1>
        <div class="desc">${esc(cfg.desc || '')}</div>
        <div class="dh-ops">
          <button class="btn-primary" id="dtPlayAll"><svg><use href="#i-play"/></svg>播放全部</button>
          <button class="btn-line" id="dtCacheAll"><svg><use href="#i-download"/></svg>缓存全部</button>
          <button class="btn-line" id="dtOnlyPlayable">仅显示可播放</button>
        </div>
      </div>`;
    $('#dtPlayAll').onclick = () => playList(cfg.list.filter((t) => t.playable), 0, true);
    $('#dtCacheAll').onclick = async () => {
      const list = cfg.list.filter((t) => t.playable && !t.cached);
      if (!list.length) { toast('都已缓存过了'); return; }
      toast('开始缓存 ' + list.length + ' 首…');
      let ok = 0;
      for (const t of list) {
        const r = await api.cacheTrack(t.id);
        if (r.ok) { t.cached = true; ok++; }
        refreshRowStates();
      }
      toast('缓存完成：' + ok + '/' + list.length);
      updateSideStat();
    };
    let onlyPlayable = false;
    $('#dtOnlyPlayable').onclick = () => {
      onlyPlayable = !onlyPlayable;
      $('#dtOnlyPlayable').textContent = onlyPlayable ? '显示全部' : '仅显示可播放';
      renderTable($('#detailTracks'), onlyPlayable ? cfg.list.filter((t) => t.playable) : cfg.list, true);
    };
    renderTable($('#detailTracks'), cfg.list, true);
  }

  function openPlaylist(pid) {
    const p = PLAYLISTS.find((x) => x.id === pid);
    if (!p) return;
    const list = state.tracks.filter(p.match);
    showDetail({
      kind: '民族歌单', title: p.name, desc: p.desc, icon: p.icon,
      img: list[0] ? coverPath(list[0].cover) : '', list
    });
    document.querySelector(`.side-item[data-pl="${pid}"]`);
  }

  function openLibrary() {
    showDetail({
      kind: '曲库', title: '全部曲库 · ' + (state.meta.group || '布依族'),
      desc: `共收录 ${state.tracks.length} 首布依族相关曲目，其中 ${state.tracks.filter((t) => t.playable).length} 首当前可播放。`,
      icon: '布', list: state.tracks.slice()
    });
  }
  function openFavorites() {
    const list = state.tracks.filter((t) => state.favorites.has(t.id));
    showDetail({ kind: '我的音乐', title: '我喜欢的', desc: '你收藏的布依族歌曲都会出现在这里。', icon: '心', list });
  }
  function openHistory() {
    const list = state.history.map((id) => byId(id)).filter(Boolean);
    showDetail({ kind: '我的音乐', title: '播放历史', desc: '最近播放过的曲目。', icon: '史', list });
  }
  function openCache() {
    const list = state.tracks.filter((t) => t.cached);
    showDetail({ kind: '本地', title: '本地缓存', desc: '已下载到本地的曲目，离线也能听。', icon: '存', list });
    api.cacheStats().then((s) => {
      toast(`已缓存 ${s.count} 首 · ${(s.size / 1048576).toFixed(1)} MB`);
    });
  }

  /* ---------------- 搜索 ---------------- */
  function doSearch(kw) {
    kw = kw.trim();
    if (!kw) return;
    const k = kw.toLowerCase();
    const list = state.tracks.filter((t) =>
      (t.title + t.artist + t.album).toLowerCase().includes(k));
    showDetail({
      kind: '搜索结果', title: '“' + kw + '”', desc: `找到 ${list.length} 首相关曲目`, icon: '搜', list
    });
    $('#searchPanel').classList.remove('show');
  }

  function renderSuggest(kw) {
    const panel = $('#searchPanel');
    kw = kw.trim();
    if (!kw) { panel.classList.remove('show'); return; }
    const k = kw.toLowerCase();
    const list = state.tracks.filter((t) =>
      (t.title + t.artist + t.album).toLowerCase().includes(k)).slice(0, 12);
    if (!list.length) { panel.classList.remove('show'); return; }
    panel.innerHTML = list.map((t) =>
      `<div class="sb-item" data-id="${t.id}"><span>${esc(t.title)}</span><em>${esc(t.artist)}</em></div>`).join('');
    panel.classList.add('show');
    panel.querySelectorAll('.sb-item').forEach((el) => {
      el.onclick = () => { const t = byId(el.dataset.id); playList([t], 0); panel.classList.remove('show'); };
    });
  }

  /* ---------------- 文化页 ---------------- */
  function renderCulture() {
    $('#culturePage').innerHTML = `
      <div class="cul-hero">
        <h2>布依族 · 山歌与靛蓝的民族</h2>
        <p>布依族世代居住在南北盘江、红水河流域，以稻作农耕为生。他们用山歌记录爱情与劳作，用蜡染与织锦记录山川与星辰。
        这个播放器收录了 ${state.tracks.length} 首布依族相关曲目，愿这些声音能被听见、被记住。</p>
      </div>
      <div class="cul-cards">
        ${CULTURE.map((c) => `<div class="cul-card">
          <h3>${esc(c.t)}</h3><p>${esc(c.p)}</p>
          <div class="cul-tags">${c.tags.map((x) => `<span>${esc(x)}</span>`).join('')}</div>
        </div>`).join('')}
      </div>`;
  }

  /* ---------------- 播放器 ---------------- */
  function byId(id) { return state.tracks.find((t) => t.id === id); }

  async function playList(list, index, force) {
    if (!list || !list.length) return;
    state.queue = list.slice();
    state.qi = index;
    await playIndex(index, force);
    renderQueue();
  }

  async function playIndex(i, force) {
    if (i < 0 || i >= state.queue.length) return;
    state.qi = i;
    const t = state.queue[i];
    state.current = t;
    updatePlayerMeta(t);
    refreshRowStates();

    if (!t.playable) {
      audio.pause();
      setPlaying(false);
      toast('该曲目音源暂不可用，试试其他曲目');
      return;
    }
    $('#pbArtist').textContent = '正在获取音源…';
    const r = await api.ensureAudio(t.id);
    if (!r.ok) {
      setPlaying(false);
      $('#pbArtist').textContent = r.error || '音源获取失败';
      toast(r.error || '音源获取失败');
      if (!force) next();
      return;
    }
    t.cached = true;
    $('#pbArtist').textContent = t.artist;
    audio.src = r.src;
    try {
      await audio.play();
      setPlaying(true);
    } catch (e) {
      setPlaying(false);
    }
    pushHistory(t.id);
    refreshRowStates();
    updateSideStat();
    if (!$('#playerPage').classList.contains('hidden')) updatePlayerPage(t);
  }

  function updatePlayerMeta(t) {
    $('#pbTitle').textContent = t.title;
    $('#pbArtist').textContent = t.artist;
    const c = $('#pbCover');
    c.innerHTML = `<img src="${coverPath(t.cover)}" alt="">`;
    $('#pbHeart').classList.toggle('on', state.favorites.has(t.id));
    $('#timeAll').textContent = t.durationText || '--:--';
    $('#seekFill').style.width = '0%';
    $('#timeCur').textContent = '00:00';
  }

  function setPlaying(v) {
    state.playing = v;
    const icon = v ? '#i-pause' : '#i-play';
    $('#playIcon').innerHTML = `<use href="${icon}"/>`;
    $('#ppPlayIcon').innerHTML = `<use href="${icon}"/>`;
    $('#disc').classList.toggle('spin', v);
  }

  function next(user) {
    if (!state.queue.length) return;
    if (state.mode === 'single' && !user) { audio.currentTime = 0; audio.play(); return; }
    let i;
    if (state.mode === 'shuffle') {
      i = Math.floor(Math.random() * state.queue.length);
    } else {
      i = (state.qi + 1) % state.queue.length;
    }
    playIndex(i);
  }
  function prev() {
    if (!state.queue.length) return;
    const i = (state.qi - 1 + state.queue.length) % state.queue.length;
    playIndex(i);
  }

  function pushHistory(id) {
    state.history = [id].concat(state.history.filter((x) => x !== id)).slice(0, 200);
    api.saveStore({ history: state.history, lastTrackId: id });
  }
  function toggleFav(t) {
    if (state.favorites.has(t.id)) state.favorites.delete(t.id);
    else state.favorites.add(t.id);
    api.saveStore({ favorites: Array.from(state.favorites) });
    $('#pbHeart').classList.toggle('on', state.favorites.has(t.id));
    $('#ppFav').classList.toggle('on', state.favorites.has(state.current && state.current.id));
    toast(state.favorites.has(t.id) ? '已加入我喜欢的' : '已取消收藏');
  }

  /* ---------------- 播放页 ---------------- */
  function updatePlayerPage(t) {
    $('#ppTitle').textContent = t.title;
    $('#ppArtist').textContent = t.artist;
    $('#ppAlbum').textContent = t.album || '布依族民歌';
    $('#discCover').src = coverPath(t.cover);
    const bg = $('#ppBg');
    bg.style.backgroundImage = `url("${coverPath(t.cover)}")`;
    $('#ppFav').classList.toggle('on', state.favorites.has(t.id));
    renderLyric(t);
  }

  const HAOHUAHONG = ['好花红来好花红', '好花生在刺梨蓬', '好花生在刺梨树', '朵朵向阳朵朵红'];
  const GENERIC = ['布依族民歌', '山野之间 · 世代传唱', '（本曲暂无歌词，请欣赏）'];
  function renderLyric(t) {
    const lines = /好花红/.test(t.title) ? HAOHUAHONG : GENERIC;
    $('#lyricBox').innerHTML = `<div class="lyric-inner">` +
      lines.map((l, i) => `<div class="lyric-line ${i === 0 ? 'active' : ''}">${esc(l)}</div>`).join('') +
      `</div>`;
  }
  function tickLyric() {
    const box = $('#lyricBox');
    const inner = box.querySelector('.lyric-inner');
    if (!inner) return;
    const lines = Array.from(inner.children);
    if (!lines.length) return;
    const t = state.current;
    const dur = (t && t.duration) || audio.duration || 180;
    const idx = Math.min(lines.length - 1, Math.floor((audio.currentTime / dur) * lines.length));
    lines.forEach((l, i) => l.classList.toggle('active', i === idx));
    inner.style.transform = `translateY(${-idx * 44 + 100}px)`;
  }

  function openPlayerPage() {
    if (!state.current) { toast('先选一首歌吧'); return; }
    $('#playerPage').classList.remove('hidden');
    updatePlayerPage(state.current);
    $('#disc').classList.toggle('spin', state.playing);
  }
  function closePlayerPage() { $('#playerPage').classList.add('hidden'); }

  /* ---------------- 队列 ---------------- */
  function renderQueue() {
    const list = state.queue;
    if (!list.length) { $('#qpList').innerHTML = '<div class="empty">播放队列为空</div>'; return; }
    $('#qpList').innerHTML = list.map((t, i) => `
      <div class="qp-item ${i === state.qi ? 'on' : ''}" data-i="${i}">
        <span>${i === state.qi ? '▶' : (i + 1)}</span>
        <span class="qi">${esc(t.title)}</span>
        <span class="qt">${t.durationText}</span>
      </div>`).join('');
    $('#qpList').querySelectorAll('.qp-item').forEach((el) => {
      el.onclick = () => playIndex(+el.dataset.i);
    });
  }

  /* ---------------- 事件绑定 ---------------- */
  const MODE_ICON = { loop: '#i-loop', single: '#i-single', shuffle: '#i-shuffle' };
  const MODE_TEXT = { loop: '列表循环', single: '单曲循环', shuffle: '随机播放' };

  function bindEvents() {
    // 侧边栏
    document.querySelector('.side-scroll').addEventListener('click', (e) => {
      const el = e.target.closest('.side-item[data-view]');
      if (!el) return;
      const v = el.dataset.view;
      if (v === 'home') setView('home');
      else if (v === 'library') openLibrary();
      else if (v === 'favorites') openFavorites();
      else if (v === 'history') openHistory();
      else if (v === 'cache') openCache();
      else if (v === 'culture') setView('culture');
    });

    // 窗口
    $('#btnMin').onclick = () => api.winMin();
    $('#btnMax').onclick = () => api.winMax();
    $('#btnClose').onclick = () => api.winClose();
    $('#navBack').onclick = () => { if (state.view !== 'home') { setView('home'); } };

    // 搜索
    $('#searchInput').oninput = (e) => renderSuggest(e.target.value);
    $('#searchInput').onkeydown = (e) => { if (e.key === 'Enter') doSearch(e.target.value); };
    $('#searchInput').onblur = () => setTimeout(() => $('#searchPanel').classList.remove('show'), 200);

    // 播放控制
    $('#btnPlay').onclick = () => {
      if (!state.current) {
        const pool = state.tracks.filter((t) => t.playable);
        if (pool.length) playList(pool, Math.floor(Math.random() * pool.length));
        return;
      }
      if (audio.paused) audio.play().catch(() => { }); else audio.pause();
    };
    $('#btnNext').onclick = () => next(true);
    $('#btnPrev').onclick = () => prev();
    $('#btnMode').onclick = () => {
      const order = ['loop', 'single', 'shuffle'];
      state.mode = order[(order.indexOf(state.mode) + 1) % 3];
      $('#modeIcon').innerHTML = `<use href="${MODE_ICON[state.mode]}"/>`;
      toast(MODE_TEXT[state.mode]);
    };

    // 进度
    const seek = (e) => {
      const bar = $('#seekBar');
      const r = bar.getBoundingClientRect();
      const p = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      if (audio.duration) audio.currentTime = p * audio.duration;
    };
    $('#seekBar').onmousedown = (e) => { seek(e); const mv = (ev) => seek(ev); const up = () => { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); }; document.addEventListener('mousemove', mv); document.addEventListener('mouseup', up); };

    // 音量
    const setVol = (e) => {
      const r = $('#volBar').getBoundingClientRect();
      const v = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      state.volume = v; audio.volume = v; state.muted = false;
      $('#volFill').style.width = (v * 100) + '%';
      $('#volIcon').innerHTML = `<use href="#i-volume"/>`;
      api.saveStore({ volume: v });
    };
    $('#volBar').onmousedown = (e) => { setVol(e); const mv = (ev) => setVol(ev); const up = () => { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up); }; document.addEventListener('mousemove', mv); document.addEventListener('mouseup', up); };
    $('#btnMute').onclick = () => {
      state.muted = !state.muted;
      audio.muted = state.muted;
      $('#volIcon').innerHTML = `<use href="#${state.muted ? 'i-mute' : 'i-volume'}"/>`;
    };

    // 播放页 / 队列
    $('#pbCover').onclick = openPlayerPage;
    $('#btnLyric').onclick = openPlayerPage;
    $('#ppClose').onclick = closePlayerPage;
    $('#ppPlay').onclick = () => { if (audio.paused) audio.play().catch(() => { }); else audio.pause(); };
    $('#ppNext').onclick = () => next(true);
    $('#ppPrev').onclick = () => prev();
    $('#ppFav').onclick = () => state.current && toggleFav(state.current);
    $('#ppDl').onclick = async () => {
      if (!state.current) return;
      const r = await api.cacheTrack(state.current.id);
      toast(r.ok ? '已缓存到本地' : '缓存失败：' + (r.error || ''));
    };
    $('#btnQueue').onclick = () => {
      const p = $('#queuePanel');
      p.classList.toggle('hidden');
      if (!p.classList.contains('hidden')) renderQueue();
    };
    $('#qpClose').onclick = () => $('#queuePanel').classList.add('hidden');
    $('#pbHeart').onclick = () => state.current && toggleFav(state.current);
    $('#btnPlayDaily').onclick = () => {
      const list = Array.from($('#dailyGrid').querySelectorAll('.mcard')).map((n) => byId(n.dataset.id));
      playList(list, 0, true);
    };

    // 音频事件
    audio.addEventListener('play', () => setPlaying(true));
    audio.addEventListener('pause', () => setPlaying(false));
    audio.addEventListener('ended', () => next());
    audio.addEventListener('timeupdate', () => {
      if (!audio.duration) return;
      const p = audio.currentTime / audio.duration;
      $('#seekFill').style.width = (p * 100) + '%';
      $('#timeCur').textContent = fmtTime(audio.currentTime);
      if (!state.current || !state.current.duration) $('#timeAll').textContent = fmtTime(audio.duration);
      tickLyric();
    });
    audio.addEventListener('loadedmetadata', () => {
      $('#timeAll').textContent = fmtTime(audio.duration);
    });
    audio.addEventListener('error', () => {
      if (!audio.src) return;
      setPlaying(false);
      toast('播放失败，音源可能已失效');
    });

    // 快捷键
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT') return;
      if (e.code === 'Space') { e.preventDefault(); if (audio.paused) audio.play().catch(() => { }); else audio.pause(); }
      if (e.code === 'Escape') { closePlayerPage(); $('#queuePanel').classList.add('hidden'); }
      if (e.code === 'ArrowRight' && e.ctrlKey) next(true);
      if (e.code === 'ArrowLeft' && e.ctrlKey) prev();
    });
  }

  init();
})();
