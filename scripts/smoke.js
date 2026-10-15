// 冒烟测试：启动应用 8 秒，收集渲染进程日志后退出
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const root = path.join(__dirname, '..');
const electron = require('electron');

const env = { ...process.env, BUYI_DEBUG: '1' };
delete env.ELECTRON_RUN_AS_NODE;
const child = spawn(electron, [root], {
  env,
  stdio: ['ignore', 'pipe', 'pipe']
});

let out = '';
child.stdout.on('data', d => { out += d.toString(); });
child.stderr.on('data', d => { out += d.toString(); });

setTimeout(() => {
  child.kill();
  console.log('===== 日志 =====');
  console.log(out || '(无输出)');
  process.exit(0);
}, 8000);
