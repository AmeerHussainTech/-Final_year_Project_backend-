/**
 * Electron Main Process — Presenova Desktop App
 * Wraps the web app in a native desktop window for Windows & macOS.
 */

const { app, BrowserWindow, shell, Menu, Tray, nativeImage } = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development';

// The production URL — points to your Firebase Hosting URL
const PROD_URL = 'https://fyp-integration.web.app';
// In dev mode, point to local Vite dev server
const DEV_URL = 'http://localhost:3000';

let mainWindow = null;
let tray = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'Presenova — AI Presentation Coach',
    icon: path.join(__dirname, '../public/icons/icon-512.png'),
    backgroundColor: '#0f0f1a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true,
    },
    show: false, // show only after ready-to-show
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
  });

  // Load the app: in production prefer local bundle if present, fallback to live web app
  if (isDev) {
    mainWindow.loadURL(DEV_URL);
  } else {
    const localDistPath = path.join(__dirname, '../dist/index.html');
    if (require('fs').existsSync(localDistPath)) {
      mainWindow.loadFile(localDistPath);
    } else {
      mainWindow.loadURL(PROD_URL);
    }
  }

  // Show window when content is loaded (prevents white flash)
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open external links in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  const iconPath = path.join(__dirname, '../public/icons/icon-192.png');
  try {
    const icon = nativeImage.createFromPath(iconPath);
    tray = new Tray(icon.resize({ width: 16, height: 16 }));
    tray.setToolTip('Presenova — AI Presentation Coach');
    tray.on('click', () => {
      if (mainWindow) mainWindow.show();
      else createWindow();
    });
  } catch (e) {
    // Tray icon not critical
  }
}

// App menu
function createMenu() {
  const template = [
    {
      label: 'Presenova',
      submenu: [
        { label: 'About Presenova', role: 'about' },
        { type: 'separator' },
        { label: 'Hide', accelerator: 'CmdOrCtrl+H', role: 'hide' },
        { type: 'separator' },
        { label: 'Quit', accelerator: 'CmdOrCtrl+Q', role: 'quit' },
      ],
    },
    {
      label: 'Navigate',
      submenu: [
        { label: 'Dashboard', accelerator: 'CmdOrCtrl+1', click: () => mainWindow?.loadURL(`${isDev ? DEV_URL : PROD_URL}/analytics`) },
        { label: 'Document Analyzer', accelerator: 'CmdOrCtrl+2', click: () => mainWindow?.loadURL(`${isDev ? DEV_URL : PROD_URL}/analyzer`) },
        { label: 'Speech Analyzer', accelerator: 'CmdOrCtrl+3', click: () => mainWindow?.loadURL(`${isDev ? DEV_URL : PROD_URL}/speech`) },
        { label: 'AI Coach', accelerator: 'CmdOrCtrl+4', click: () => mainWindow?.loadURL(`${isDev ? DEV_URL : PROD_URL}/practice`) },
        { label: 'Presentation Rewriter', accelerator: 'CmdOrCtrl+5', click: () => mainWindow?.loadURL(`${isDev ? DEV_URL : PROD_URL}/presentation-rewriter`) },
      ],
    },
    {
      label: 'View',
      submenu: [
        { label: 'Reload', accelerator: 'CmdOrCtrl+R', role: 'reload' },
        { label: 'Toggle DevTools', accelerator: 'F12', role: 'toggleDevTools' },
        { type: 'separator' },
        { label: 'Zoom In', role: 'zoomIn' },
        { label: 'Zoom Out', role: 'zoomOut' },
        { label: 'Reset Zoom', role: 'resetZoom' },
        { type: 'separator' },
        { label: 'Toggle Fullscreen', role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { label: 'Undo', role: 'undo' },
        { label: 'Redo', role: 'redo' },
        { type: 'separator' },
        { label: 'Cut', role: 'cut' },
        { label: 'Copy', role: 'copy' },
        { label: 'Paste', role: 'paste' },
        { label: 'Select All', role: 'selectAll' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.whenReady().then(() => {
  createWindow();
  createMenu();
  createTray();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
