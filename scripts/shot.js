// 截图工具：node scripts/shot.js <输出路径> [等待毫秒]
const { spawn } = require('child_process');
const path = require('path');
const electron = require('electron');

const out = process.argv[2] || path.join(process.cwd(), 'shot.png');
const wait = parseInt(process.argv[3] || '7000', 10);

const env = { ...process.env, BUYI_DEBUG: '1', BUYI_SHOT: out };
delete env.ELECTRON_RUN_AS_NODE;

const child = spawn(electron, [path.join(__dirname, '..')], { env, stdio: ['ignore', 'pipe', 'pipe'] });
let log = '';
child.stdout.on('data', (d) => { log += d.toString(); });
child.stderr.on('data', (d) => { log += d.toString(); });
setTimeout(() => {
  child.kill();
  console.log(log.split('\n').filter(l => l.includes('[shot]') || l.includes('[renderer]')).join('\n').slice(0, 2000));
}, wait);
