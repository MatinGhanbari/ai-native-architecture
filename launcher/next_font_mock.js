// برای اجرای بدون اینترنت: next/font/google به جای Google Fonts این پاسخ‌ها را می‌خواند.
// لانچر NEXT_FONT_GOOGLE_MOCKED_RESPONSES را به این فایل اشاره می‌دهد؛ فایل‌های فونت در part-01/demo/vendor/fonts هستند.
const path = require("path");
const DIR = path.resolve(__dirname, "..", "part-01", "demo", "vendor", "fonts");
// next فقط مسیرهایی را که با / شروع شوند از دیسک می‌خواند؛ در ویندوز حرف درایو حذف می‌شود (همان درایو جاری).
const P = n => path.join(DIR, n).replace(/^[A-Za-z]:/, "").split(path.sep).join("/");
const CSS = {
 "Vazirmatn": [
  [
   "arabic",
   "@font-face {\n  font-family: 'Vazirmatn';\n  font-style: normal;\n  font-weight: 100 900;\n  font-display: swap;\n  src: url(__F__vazirmatn-arabic-100-900.woff2) format('woff2');\n  unicode-range: U+0600-06FF, U+0750-077F, U+0870-0891, U+0897-08E1, U+08E3-08FF, U+200C-200E, U+2010-2011, U+204F, U+2E41, U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC, U+102E0-102FB, U+10E60-10E7E, U+10EC2-10EC7, U+10EC9-10EEE, U+10EF0-10EFF, U+1EE00-1EE03, U+1EE05-1EE1F, U+1EE21-1EE22, U+1EE24, U+1EE27, U+1EE29-1EE32, U+1EE34-1EE37, U+1EE39, U+1EE3B, U+1EE42, U+1EE47, U+1EE49, U+1EE4B, U+1EE4D-1EE4F, U+1EE51-1EE52, U+1EE54, U+1EE57, U+1EE59, U+1EE5B, U+1EE5D, U+1EE5F, U+1EE61-1EE62, U+1EE64, U+1EE67-1EE6A, U+1EE6C-1EE72, U+1EE74-1EE77, U+1EE79-1EE7C, U+1EE7E, U+1EE80-1EE89, U+1EE8B-1EE9B, U+1EEA1-1EEA3, U+1EEA5-1EEA9, U+1EEAB-1EEBB, U+1EEF0-1EEF1;\n}"
  ],
  [
   "latin-ext",
   "@font-face {\n  font-family: 'Vazirmatn';\n  font-style: normal;\n  font-weight: 100 900;\n  font-display: swap;\n  src: url(__F__vazirmatn-latin-ext-100-900.woff2) format('woff2');\n  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;\n}"
  ],
  [
   "latin",
   "@font-face {\n  font-family: 'Vazirmatn';\n  font-style: normal;\n  font-weight: 100 900;\n  font-display: swap;\n  src: url(__F__vazirmatn-latin-100-900.woff2) format('woff2');\n  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;\n}"
  ]
 ],
 "JetBrains Mono": [
  [
   "latin-ext",
   "@font-face {\n  font-family: 'JetBrains Mono';\n  font-style: normal;\n  font-weight: 400;\n  font-display: swap;\n  src: url(__F__jetbrains-mono-latin-ext-400.woff2) format('woff2');\n  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;\n}"
  ],
  [
   "latin",
   "@font-face {\n  font-family: 'JetBrains Mono';\n  font-style: normal;\n  font-weight: 400;\n  font-display: swap;\n  src: url(__F__jetbrains-mono-latin-400.woff2) format('woff2');\n  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;\n}"
  ],
  [
   "latin-ext",
   "@font-face {\n  font-family: 'JetBrains Mono';\n  font-style: normal;\n  font-weight: 500;\n  font-display: swap;\n  src: url(__F__jetbrains-mono-latin-ext-500.woff2) format('woff2');\n  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;\n}"
  ],
  [
   "latin",
   "@font-face {\n  font-family: 'JetBrains Mono';\n  font-style: normal;\n  font-weight: 500;\n  font-display: swap;\n  src: url(__F__jetbrains-mono-latin-500.woff2) format('woff2');\n  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;\n}"
  ],
  [
   "latin-ext",
   "@font-face {\n  font-family: 'JetBrains Mono';\n  font-style: normal;\n  font-weight: 600;\n  font-display: swap;\n  src: url(__F__jetbrains-mono-latin-ext-600.woff2) format('woff2');\n  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;\n}"
  ],
  [
   "latin",
   "@font-face {\n  font-family: 'JetBrains Mono';\n  font-style: normal;\n  font-weight: 600;\n  font-display: swap;\n  src: url(__F__jetbrains-mono-latin-600.woff2) format('woff2');\n  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;\n}"
  ]
 ],
 "IBM Plex Mono": [
  [
   "latin-ext",
   "@font-face {\n  font-family: 'IBM Plex Mono';\n  font-style: normal;\n  font-weight: 400;\n  font-display: swap;\n  src: url(__F__ibm-plex-mono-latin-ext-400.woff2) format('woff2');\n  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;\n}"
  ],
  [
   "latin",
   "@font-face {\n  font-family: 'IBM Plex Mono';\n  font-style: normal;\n  font-weight: 400;\n  font-display: swap;\n  src: url(__F__ibm-plex-mono-latin-400.woff2) format('woff2');\n  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;\n}"
  ],
  [
   "latin-ext",
   "@font-face {\n  font-family: 'IBM Plex Mono';\n  font-style: normal;\n  font-weight: 500;\n  font-display: swap;\n  src: url(__F__ibm-plex-mono-latin-ext-500.woff2) format('woff2');\n  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;\n}"
  ],
  [
   "latin",
   "@font-face {\n  font-family: 'IBM Plex Mono';\n  font-style: normal;\n  font-weight: 500;\n  font-display: swap;\n  src: url(__F__ibm-plex-mono-latin-500.woff2) format('woff2');\n  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;\n}"
  ],
  [
   "latin-ext",
   "@font-face {\n  font-family: 'IBM Plex Mono';\n  font-style: normal;\n  font-weight: 600;\n  font-display: swap;\n  src: url(__F__ibm-plex-mono-latin-ext-600.woff2) format('woff2');\n  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;\n}"
  ],
  [
   "latin",
   "@font-face {\n  font-family: 'IBM Plex Mono';\n  font-style: normal;\n  font-weight: 600;\n  font-display: swap;\n  src: url(__F__ibm-plex-mono-latin-600.woff2) format('woff2');\n  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;\n}"
  ]
 ]
};
const build = fam => CSS[fam].map(([sub, b]) => `/* ${sub} */\n` + b.replace(/__F__([\w.-]+)/g, (_, n) => P(n))).join("\n");
// turbopack فایل mock را به JSON تبدیل می‌کند، پس کلیدها باید واقعی باشند (نشانی دقیق همان که next می‌سازد).
const BY_URL = {
  "https://fonts.googleapis.com/css2?family=Vazirmatn:wght@100..900&display=swap": build("Vazirmatn"),
  "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap": build("IBM Plex Mono"),
  "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap": build("JetBrains Mono"),
};
// webpack هم با require همین را می‌خواند؛ برای نشانی‌های دیگرِ همین سه خانواده از روی نام خانواده جواب می‌دهیم.
module.exports = new Proxy(BY_URL, { get(t, url) {
  if (typeof url !== "string") return undefined;
  if (url in t) return t[url];
  const m = /family=([^:&]+)/.exec(url); if (!m) return undefined;
  const fam = decodeURIComponent(m[1].replace(/\+/g, " "));
  return CSS[fam] ? build(fam) : undefined;
} });
