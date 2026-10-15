const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('buyi', {
  getLibrary: () => ipcRenderer.invoke('get-library'),
  ensureAudio: (id) => ipcRenderer.invoke('ensure-audio', id),
  cacheTrack: (id) => ipcRenderer.invoke('cache-track', id),
  removeCache: (id) => ipcRenderer.invoke('remove-cache', id),
  saveStore: (patch) => ipcRenderer.invoke('save-store', patch),
  cacheStats: () => ipcRenderer.invoke('cache-stats'),
  openCacheDir: () => ipcRenderer.invoke('open-cache-dir'),
  appInfo: () => ipcRenderer.invoke('app-info'),
  onProgress: (cb) => {
    const handler = (_e, data) => cb(data);
    ipcRenderer.on('download-progress', handler);
    return () => ipcRenderer.removeListener('download-progress', handler);
  },
  winMin: () => ipcRenderer.send('win-min'),
  winMax: () => ipcRenderer.send('win-max'),
  winClose: () => ipcRenderer.send('win-close'),
  isMaximized: () => ipcRenderer.sendSync('win-is-max')
});
