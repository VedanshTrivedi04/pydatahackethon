const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

const nodeDir = path.dirname(process.execPath);
const tmpDir = path.join(os.tmpdir(), 'npm_bootstrap_' + Date.now());

console.log('Node.js location:', process.execPath);
console.log('Temp dir:', tmpDir);

function getLatestNpmUrl() {
  return new Promise((resolve, reject) => {
    https.get('https://registry.npmjs.org/npm/latest', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const pkg = JSON.parse(data);
          resolve(pkg.dist.tarball);
        } catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, (res) => {
      if (res.statusCode === 302 || res.statusCode === 301) {
        file.close();
        return downloadFile(res.headers.location, dest).then(resolve).catch(reject);
      }
      res.pipe(file);
      file.on('finish', () => { file.close(); resolve(); });
    }).on('error', (err) => { fs.unlink(dest, () => {}); reject(err); });
  });
}

async function main() {
  try {
    fs.mkdirSync(tmpDir, { recursive: true });
    const tarballPath = path.join(tmpDir, 'npm.tgz');

    console.log('Fetching npm registry...');
    const tarballUrl = await getLatestNpmUrl();
    console.log('Downloading:', tarballUrl);
    await downloadFile(tarballUrl, tarballPath);

    console.log('Extracting...');
    execSync(`tar -xzf "${tarballPath}" -C "${tmpDir}"`, { stdio: 'inherit' });

    const npmCliPath = path.join(tmpDir, 'package', 'bin', 'npm-cli.js');
    const frontendDir = 'd:\\pydata2.0\\pydatahackethon\\frontend';

    console.log('\nRunning npm install in frontend...');
    execSync(`"${process.execPath}" "${npmCliPath}" install`, {
      cwd: frontendDir,
      stdio: 'inherit'
    });

    console.log('\n✅ npm install complete! Starting Vite...');
    const viteCliPath = path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js');
    execSync(`"${process.execPath}" "${viteCliPath}"`, {
      cwd: frontendDir,
      stdio: 'inherit'
    });

  } catch (err) {
    console.error('Error:', err.message);
  }
}

main();
