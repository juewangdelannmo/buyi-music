// afterPack 钩子：用自带的 rcedit 写入图标与版本信息
// （本机 7z 无法创建符号链接，electron-builder 自带的 winCodeSign 无法解压，故跳过其签名/编辑步骤）
const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

module.exports = async function (context) {
  const rcedit = path.join(__dirname, '..', 'tools', 'rcedit-x64.exe');
  const icon = path.join(__dirname, '..', 'build', 'icon.ico');
  if (!fs.existsSync(rcedit) || !fs.existsSync(icon)) {
    console.log('[afterPack] 跳过（缺少 rcedit 或图标）');
    return;
  }
  const exe = path.join(context.appOutDir, context.packager.appInfo.productFilename + '.exe');
  if (!fs.existsSync(exe)) {
    console.log('[afterPack] 未找到 ' + exe);
    return;
  }
  const args = [
    exe,
    '--set-icon', icon,
    '--set-version-string', 'CompanyName', '布依音',
    '--set-version-string', 'ProductName', '布依音 · 布依族民族音乐播放器',
    '--set-version-string', 'FileDescription', '布依音 · 布依族民族音乐播放器',
    '--set-version-string', 'LegalCopyright', 'Copyright © 2026',
    '--set-file-version', context.packager.appInfo.version,
    '--set-product-version', context.packager.appInfo.version
  ];
  try {
    execFileSync(rcedit, args, { stdio: 'pipe' });
    console.log('[afterPack] 图标与版本信息已写入 ' + path.basename(exe));
  } catch (e) {
    console.log('[afterPack] rcedit 失败: ' + (e.message || e));
  }
};
