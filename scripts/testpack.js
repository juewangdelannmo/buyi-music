// 验证打包后的应用：node scripts/testpack.js
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const EXE = path.join(__dirname, '..', 'dist', 'win-unpacked', '布依音.exe');
const SHOT = path.join(process.cwd(), 'shot-packed.png');
const LOG = path.join(process.cwd(), 'testpack.log');

if (!fs.existsSync(EXE)) {
  console.log('未找到 ' + EXE);
  process.exit(1);
}

const env = { ...process.env, BUYI_DEBUG: '1', BUYI_SHOT: SHOT };
delete env.ELECTRON_RUN_AS_NODE;

const child = spawn(EXE, ['--testplay'], { env, stdio: ['ignore', 'pipe', 'pipe'] });
let log = '';
child.stdout.on('data', (d) => { log += d.toString(); });
child.stderr.on('data', (d) => { log += d.toString(); });

setTimeout(() => {
  try { child.kill(); } catch (e) { }
  fs.writeFileSync(LOG, log, 'utf8');
  console.log(log.split('\n')
    .filter((l) => /\[TEST\]|\[shot\]|\[renderer\]\[[123]\]|Error|错误|失败/.test(l))
    .join('\n').slice(0, 3000) || '(无匹配日志)');
  console.log('完整日志 -> ' + LOG);
  process.exit(0);
}, 40000);
