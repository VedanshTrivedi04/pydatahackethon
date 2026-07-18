/**
 * Bootstrap npm using Node.js built-in modules.
 * Downloads npm tarball and installs it globally.
 */
const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

const nodeDir = path.dirname(process.execPath);
const tmpDir = path.join(os.tmpdir(), 'npm_bootstrap_' + Date.now());

console.log('Node.js location:', process.execPath);
console.log('Node.js dir:', nodeDir);
console.log('Temp dir:', tmpDir);

// Step 1: Get latest npm tarball URL
function getLatestNpmUrl() {
  return new Promise((resolve, reject) => {
    https.get('https://registry.npmjs.org/npm/latest', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const pkg = JSON.parse(data);
          const tarball = pkg.dist.tarball;
          console.log('npm tarball URL:', tarball);
          resolve(tarball);
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

// Step 2: Download tarball
function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    console.log('Downloading npm...');
    const file = fs.createWriteStream(dest);
    https.get(url, (res) => {
      // Handle redirects
      if (res.statusCode === 302 || res.statusCode === 301) {
        file.close();
        return downloadFile(res.headers.location, dest).then(resolve).catch(reject);
      }
      res.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log('Download complete:', dest);
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

async function main() {
  try {
    // Create temp directory
    fs.mkdirSync(tmpDir, { recursive: true });
    
    const tarballPath = path.join(tmpDir, 'npm.tgz');
    
    // Get URL and download
    const tarballUrl = await getLatestNpmUrl();
    await downloadFile(tarballUrl, tarballPath);
    
    // Extract tarball
    console.log('Extracting npm...');
    execSync(`tar -xzf "${tarballPath}" -C "${tmpDir}"`, { stdio: 'inherit' });
    
    const npmCliPath = path.join(tmpDir, 'package', 'bin', 'npm-cli.js');
    console.log('npm-cli.js path:', npmCliPath);
    
    if (fs.existsSync(npmCliPath)) {
      console.log('\n✅ npm downloaded! Running npm install from extracted package...');
      
      // Run npm install in frontend dir
      const frontendDir = path.dirname(__filename);
      execSync(`"${process.execPath}" "${npmCliPath}" install`, {
        cwd: frontendDir,
        stdio: 'inherit',
        env: { ...process.env, npm_config_cache: path.join(tmpDir, 'cache') }
      });
      
      console.log('\n✅ npm install complete!');
      console.log('\n🚀 Starting Vite dev server...');
      
      // Start vite
      const viteCliPath = path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js');
      if (fs.existsSync(viteCliPath)) {
        require(viteCliPath);
      } else {
        console.log('Run: node node_modules/vite/bin/vite.js');
      }
    } else {
      console.error('npm-cli.js not found at:', npmCliPath);
    }
  } catch (err) {
    console.error('Error:', err.message);
  }
}

main();
