// 自动播放链路验证：node scripts/testplay.js
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const electron = require('electron');

const SHOT = path.join(process.cwd(), 'shot-play.png');
const LOG = path.join(process.cwd(), 'testplay.log');
const env = { ...process.env, BUYI_DEBUG: '1', BUYI_SHOT: SHOT };
delete env.ELECTRON_RUN_AS_NODE;

const child = spawn(electron, [path.join(__dirname, '..'), '--testplay'], {
  env, stdio: ['ignore', 'pipe', 'pipe']
});
let log = '';
child.stdout.on('data', (d) => { log += d.toString(); });
child.stderr.on('data', (d) => { log += d.toString(); });

setTimeout(() => {
  try { child.kill(); } catch (e) { }
  fs.writeFileSync(LOG, log, 'utf8');
  const useful = log.split('\n')
    .filter((l) => /\[TEST\]|\[shot\]|\[renderer\]\[[123]\]/.test(l) || /Error|error|失败/.test(l))
    .join('\n');
  console.log(useful.slice(0, 4000) || '(无匹配日志)');
  console.log('完整日志 -> ' + LOG);
  process.exit(0);
}, 45000);
