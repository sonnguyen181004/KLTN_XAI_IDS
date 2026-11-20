/**
 * DDoS Learning Hub — demos/terminal.js
 * Mini Terminal gias lap voi 17 lenh hoc thuat
 */
const TerminalDemo = (function () {
  let output, input, form;
  let history = [];
  let historyIdx = -1;
  const COMMANDS = ['help','clear','ping','whois','tcpdump','nmap','ddos','botnet','ids','shap','lime','status','syn-cookie','ratelimit','waf','history','matrix'];
  const c = {
    green:  s => `<span class="t-green">${s}</span>`,
    cyan:   s => `<span class="t-cyan">${s}</span>`,
    red:    s => `<span class="t-red">${s}</span>`,
    yellow: s => `<span class="t-yellow">${s}</span>`,
    dim:    s => `<span class="t-dim">${s}</span>`,
    white:  s => `<span class="t-white">${s}</span>`,
  };
  function rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
  function randIP() { return `${rand(1,254)}.${rand(0,255)}.${rand(0,255)}.${rand(1,254)}`; }
  function sep() { return c.dim('─'.repeat(56)); }
  function printLine(html, delay = 0) {
    return new Promise(resolve => {
      setTimeout(() => {
        const div = document.createElement('div');
        div.className = 'tline';
        div.innerHTML = html;
        output.appendChild(div);
        output.scrollTop = output.scrollHeight;
        resolve();
      }, delay);
    });
  }
  async function printLines(lines, gap = 35) {
    for (let i = 0; i < lines.length; i++) {
      await printLine(lines[i], i * gap);
    }
  }
  function printPromptLine(cmd) {
    const div = document.createElement('div');
    div.className = 'tline';
    div.innerHTML = `${c.green('root@ddos-lab')}${c.white(':')}${c.cyan('~')}${c.white('$ ')}${c.white(cmd)}`;
    output.appendChild(div);
  }
  const handlers = {
    help() {
      return printLines([
        c.cyan('╔══════════════════════════════════════════════════════╗'),
        c.cyan('║') + c.yellow('      DDoS Learning Hub — Danh sach lenh            ') + c.cyan('║'),
        c.cyan('╚══════════════════════════════════════════════════════╝'),
        '',
        c.cyan('  Mang & Phan tich:'),
        `  ${c.green('ping')} ${c.dim('<ip>')}         Gia lap ICMP ping`,
        `  ${c.green('whois')} ${c.dim('<ip>')}        Xem ISP, quoc gia, rui ro`,
        `  ${c.green('tcpdump')}            Stream 6 packet thoi gian thuc`,
        `  ${c.green('nmap')}               Quet cong gia lap`,
        '',
        c.cyan('  Tan cong DDoS:'),
        `  ${c.green('ddos')}               Menu 4 loai tan cong`,
        `  ${c.green('ddos')} ${c.dim('--syn/--udp/--http/--amp')}  Chi tiet tung loai`,
        `  ${c.green('botnet')}             Kien truc Botnet + so do ASCII`,
        '',
        c.cyan('  Phong thu & Bao mat:'),
        `  ${c.green('ids')}                IDS vs IPS, Signature vs ML`,
        `  ${c.green('syn-cookie')}         Co che SYN Cookie`,
        `  ${c.green('ratelimit')}          Rate Limiting + Token Bucket`,
        `  ${c.green('waf')}                Web Application Firewall`,
        '',
        c.cyan('  AI & XAI:'),
        `  ${c.green('shap')}               Minh hoa SHAP Values`,
        `  ${c.green('lime')}               LIME Local Surrogate Model`,
        '',
        c.cyan('  He thong:'),
        `  ${c.green('status')}             CPU, RAM, Firewall, IDS`,
        `  ${c.green('history')}            10 lenh gan nhat`,
        `  ${c.green('clear')}              Xoa man hinh`,
        `  ${c.green('matrix')}             Easter egg`,
        '',
        c.dim('Tab: autocomplete  |  Up/Down: lich su lenh'),
        sep(),
      ]);
    },
    clear() { output.innerHTML = ''; return Promise.resolve(); },
    async ping(args) {
      const ip = args[0] || '8.8.8.8';
      await printLine(`${c.cyan('PING')} ${c.white(ip)}${c.dim(': 56 data bytes')}`);
      for (let i = 1; i <= 4; i++) {
        const ms = rand(12, 80);
        await new Promise(r => setTimeout(r, 380));
        await printLine(`${c.dim('64 bytes from')} ${c.green(ip)}${c.dim(': icmp_seq=')}${c.white(i)} ${c.dim('TTL=128 time=')}${c.yellow(ms + ' ms')}`);
      }
      await new Promise(r => setTimeout(r, 200));
      await printLines([
        '',
        c.dim(`--- ${ip} ping statistics ---`),
        `${c.white('4')} ${c.dim('packets transmitted,')} ${c.green('4 received,')} ${c.dim('0% packet loss')}`,
        `${c.dim('rtt min/avg/max =')} ${c.yellow('12/38/80 ms')}`,
        sep(),
      ]);
    },
    whois(args) {
      const ip = args[0] || randIP();
      const isps = ['VNPT Vietnam','Viettel Telecom','FPT Telecom','China Telecom','Cogent Communications'];
      const cities = ['Ha Noi','Ho Chi Minh','Beijing','Moscow','New York'];
      const countries = ['Vietnam','China','Russia','USA','Brazil'];
      const idx = rand(0, 4);
      const isp = isps[idx], city = cities[idx], country = countries[idx];
      const risk = rand(0,1) ? c.red('HIGH - Botnet suspected') : c.green('LOW');
      return printLines([
        c.cyan('WHOIS Lookup Result'),
        sep(),
        `  ${c.dim('IP Address  :')} ${c.white(ip)}`,
        `  ${c.dim('ISP         :')} ${c.white(isp)}`,
        `  ${c.dim('ASN         :')} ${c.cyan('AS' + rand(1000,65000))}`,
        `  ${c.dim('Country     :')} ${c.white(country)}`,
        `  ${c.dim('City        :')} ${c.white(city)}`,
        `  ${c.dim('Risk Level  :')} ${risk}`,
        sep(),
      ]);
    },
    async tcpdump() {
      const protos = ['TCP','UDP','ICMP','HTTP','DNS','TLS'];
      const flags = ['[SYN]','[ACK]','[SYN,ACK]','[FIN]','[RST]','[PSH,ACK]'];
      await printLine(c.cyan('tcpdump: listening on eth0...'));
      for (let i = 0; i < 6; i++) {
        await new Promise(r => setTimeout(r, 380));
        const now = new Date();
        const ts = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
        const proto = protos[rand(0,5)], flag = flags[rand(0,5)];
        const bytes = rand(40,1500);
        const src = randIP() + ':' + rand(1024,65535);
        const dst = '103.21.4.100:' + [80,443,53][rand(0,2)];
        const fc = flag.includes('SYN') && !flag.includes('ACK') ? c.red(flag) : c.green(flag);
        await printLine(`${c.dim(ts)} ${c.cyan(proto)} ${c.white(src)} ${c.dim('→')} ${c.white(dst)} ${fc} ${c.dim(bytes+'B')}`);
      }
      await printLine(c.dim('6 packets captured.'));
      await printLine(sep());
    },
    nmap() {
      const ports = [
        {p:21,s:'FTP',st:'closed'},{p:22,s:'SSH',st:'open'},
        {p:25,s:'SMTP',st:'filtered'},{p:80,s:'HTTP',st:'open'},
        {p:443,s:'HTTPS',st:'open'},{p:3306,s:'MySQL',st:'closed'},
        {p:5432,s:'PostgreSQL',st:'closed'},{p:8080,s:'HTTP-Alt',st:'open'},
      ];
      const rows = ports.map(x => {
        const st = x.st==='open' ? c.green('open      ') : x.st==='closed' ? c.red('closed    ') : c.yellow('filtered  ');
        return `  ${c.white((x.p+'/tcp').padEnd(9))}${st}${c.cyan(x.s)}`;
      });
      return printLines([
        c.cyan('Nmap 7.94 - Scanning 103.21.4.100'),
        c.cyan('PORT      STATE     SERVICE'),
        c.dim('─'.repeat(36)),
        ...rows,
        '',
        c.dim('Done: 1 host scanned in 2.34s'),
        sep(),
      ]);
    },
    ddos(args) {
      const flag = args[0];
      if (!flag) return printLines([
        c.red('4 Loai Tan cong DDoS Pho Bien'),
        sep(),
        `  ${c.red('1.')} ${c.yellow('SYN Flood')}        ${c.dim('ddos --syn')}`,
        `     Lam tran hang doi ket noi TCP bang goi SYN gia mao`,
        '',
        `  ${c.red('2.')} ${c.yellow('UDP Flood')}        ${c.dim('ddos --udp')}`,
        `     Ban UDP vao port ngau nhien, ep server xu ly loi ICMP`,
        '',
        `  ${c.red('3.')} ${c.yellow('HTTP Flood')}       ${c.dim('ddos --http')}`,
        `     Gui hang trieu HTTP request hop le, kho phan biet`,
        '',
        `  ${c.red('4.')} ${c.yellow('DNS Amplification')} ${c.dim('ddos --amp')}`,
        `     Khai thac DNS server khuyech dai traffic len 70x`,
        '',
        c.dim("Go 'ddos --syn/--udp/--http/--amp' de xem chi tiet."),
        sep(),
      ]);
      if (flag === '--syn') return printLines([
        c.red('SYN Flood Attack'),
        sep(),
        `${c.cyan('Nguyen ly:')} Khai thac buoc 1 TCP 3-way Handshake`,
        `  Attacker gui ${c.red('hang trieu SYN')} nhung khong bao gio gui ACK`,
        `  Server phai giu slot bo nho cho tung ket noi cho ACK`,
        `  Sau do: ${c.red('Backlog Queue = FULL → Tu choi moi ket noi')}`,
        '',
        `${c.cyan('Quy mo:')} ${c.yellow('500 Gbps+')} — Vu Dyn 2016 dung Mirai Botnet IoT`,
        `${c.cyan('Phong thu:')} ${c.green('SYN Cookie, Rate Limiter, Stateful Firewall')}`,
        sep(),
      ]);
      if (flag === '--udp') return printLines([
        c.red('UDP Flood Attack'),
        sep(),
        `${c.cyan('Nguyen ly:')} UDP khong can bat tay — gui thang vao bat ky port nao`,
        `  Attacker gui ${c.red('hang trieu UDP packet')} vao port ngau nhien`,
        `  Server khong co app lang nghe → phai tra ICMP "Port Unreachable"`,
        `  ${c.red('CPU & Bandwidth kiet suc')} xu ly ICMP response`,
        '',
        `${c.cyan('Quy mo:')} ${c.yellow('100–400 Gbps')}`,
        `${c.cyan('Phong thu:')} ${c.green('Block UDP ngoai tru DNS/NTP, Rate limit ICMP')}`,
        sep(),
      ]);
      if (flag === '--http') return printLines([
        c.red('HTTP Flood (Layer 7 DDoS)'),
        sep(),
        `${c.cyan('Nguyen ly:')} Gui HTTP request ${c.yellow('hop le ve cu phap')} voi so luong cuc lon`,
        `  GET /search?q=randomstring HTTP/1.1`,
        `  Host: target.com`,
        `  User-Agent: Mozilla/5.0 (gia mao browser)`,
        `  Server phai ${c.red('thuc thi query DB, render trang')} cho moi request`,
        '',
        `${c.cyan('Kho phat hien:')} Can ${c.green('ML-IDS')} phan tich hanh vi`,
        `${c.cyan('Phong thu:')} ${c.green('WAF, CAPTCHA, Behavioral analysis, Rate limit')}`,
        sep(),
      ]);
      if (flag === '--amp') return printLines([
        c.red('DNS Amplification Attack'),
        sep(),
        `${c.cyan('Nguyen ly:')} Dung DNS server cong cong lam ${c.yellow('"bo khuyech dai"')}`,
        `  Attacker (IP gia = IP nan nhan) gui DNS Query 60B → DNS Server`,
        `  DNS Server gui DNS Response 4000B → ${c.red('Nan nhan!')}`,
        `  He so khuyech dai: ${c.red('4000 / 60 = 67x')}`,
        `  100 Mbps botnet → ${c.red('6.7 Gbps')} traffic den nan nhan`,
        '',
        `${c.cyan('Protocol bi loi dung:')} DNS ANY, NTP, memcached (51,000x!)`,
        `${c.cyan('Phong thu:')} ${c.green('Vo hieu hoa DNS ANY query, BCP38 IP filtering')}`,
        sep(),
      ]);
      return printLines([c.red('Flag khong hop le. Dung: ddos --syn | --udp | --http | --amp')]);
    },
    botnet() {
      return printLines([
        c.yellow('Kien truc Mang Botnet'),
        sep(),
        `              ${c.red('[ HACKER ]')}`,
        `                   |`,
        `            ${c.dim('Ra lenh tan cong')}`,
        `                   |`,
        `              ${c.red('[ C2 SERVER ]')}`,
        `            ${c.dim('(Command & Control)')}`,
        `           /       |        \\`,
        `    ${c.yellow('[Zombie]')} ${c.yellow('[Zombie]')} ${c.yellow('[Zombie]')}`,
        `  ${c.dim('Camera IoT')} ${c.dim('Router')}  ${c.dim('PC nhiem doc')}`,
        `         \\         |        /`,
        `          ${c.red('vvvvvvvvvvvvvvv')}`,
        `            ${c.red('[ TARGET SERVER ] BOOM')}`,
        '',
        `${c.cyan('Cach lay nhiem:')} Quet Internet tim thiet bi mat khau mac dinh`,
        `  (admin/admin, root/1234) → upload ma doc Mirai/Mozi`,
        `${c.cyan('Quy mo:')} Mirai 2016: ${c.red('600,000+')} thiet bi IoT → ${c.red('1.1 Tbps')}`,
        sep(),
      ]);
    },
    ids() {
      return printLines([
        c.cyan('IDS vs IPS — Phat hien & Ngan chan Xam nhap'),
        sep(),
        `${c.yellow('IDS (Intrusion Detection System)')}`,
        `  Theo doi traffic → ${c.green('Phat canh bao')} khi phat hien bat thuong`,
        `  Khong tu dong chan. Chuyen gia SOC xem xet thu cong.`,
        '',
        `${c.yellow('IPS (Intrusion Prevention System)')}`,
        `  Theo doi traffic → ${c.red('Tu dong chan ngay lap tuc')}`,
        `  Rui ro: False Positive cao → chan nham nguoi dung that`,
        '',
        c.cyan('  So sanh Co che Phat hien:'),
        '',
        `  ${c.yellow('Signature-based IDS:')}`,
        `    Khop traffic voi database mau tan cong co san`,
        `    OK Nhanh, chinh xac voi tan cong da biet`,
        `    XX ${c.red('Mu voi Zero-day')} — tan cong moi hoan toan`,
        '',
        `  ${c.green('Anomaly-based ML-IDS (XAI-IDS):')}`,
        `    Hoc thoi quen traffic → phat hien ${c.green('moi bat thuong')}`,
        `    OK Phat hien Zero-day, DDoS moi chua tung gap`,
        `    XX Can du lieu training lon, giai thich bang ${c.cyan('SHAP/LIME')}`,
        sep(),
      ]);
    },
    shap() {
      return printLines([
        c.cyan('SHAP Force Plot — Phan tich Goi tin DDoS'),
        sep(),
        c.dim('Packet #48291 | Verdict: ') + c.red('DDoS Attack (89.3%)'),
        '',
        c.cyan('SHAP Values:'),
        `  Packet Rate      ${c.red('|||||||||||||||||| +0.52')} ${c.dim('Vot 42,000 pps')}`,
        `  SYN/ACK Ratio    ${c.red('||||||||||||||  +0.38')}   ${c.dim('28:1 bat thuong')}`,
        `  IP Entropy       ${c.red('||||||||||   +0.27')}      ${c.dim('IP phan tan cao')}`,
        `  Payload StdDev   ${c.green('||||        -0.12')}      ${c.dim('Goi tin dong nhat')}`,
        `  Port Diversity   ${c.green('||          -0.06')}      ${c.dim('Tap trung port 80')}`,
        '',
        `  ${c.dim('Base value:    0.50')}`,
        `  ${c.dim('Tong SHAP:    ')}${c.red('+0.39')}`,
        `  ${c.yellow('DDoS Score:   ')}${c.red('0.89 → ATTACK')}`,
        '',
        c.dim('SHAP dua tren Shapley Values (Game Theory Nobel 2012)'),
        sep(),
      ]);
    },
    lime() {
      return printLines([
        c.yellow('LIME — Local Interpretable Model-agnostic Explanations'),
        sep(),
        c.dim('Packet #48291 | LIME Local Surrogate Model'),
        '',
        `${c.cyan('Co che:')} LIME tao ${c.white('500 diem du lieu gia')} xung quanh packet nay`,
        `  Fit duong thang y = w1*x1 + w2*x2 + ... xap xi AI cuc bo`,
        '',
        c.yellow('LIME Weights:'),
        `  Packet Rate >= 40000   ${c.red('w = +0.81')} ${c.dim('Ung ho DDoS manh')}`,
        `  SYN flag = True        ${c.red('w = +0.64')} ${c.dim('Ung ho DDoS')}`,
        `  ACK flag = False       ${c.red('w = +0.43')} ${c.dim('Ung ho DDoS')}`,
        `  Payload Size <= 64B    ${c.red('w = +0.29')} ${c.dim('Goi tin rac')}`,
        `  HTTP Header = Absent   ${c.green('w = -0.15')} ${c.dim('Giam nhe nguy co')}`,
        '',
        `${c.cyan('LIME vs SHAP:')}`,
        `  SHAP: chinh xac toan hoc tuyet doi, nhat quan toan cuc`,
        `  LIME: ${c.yellow('nhanh hon')}, ket qua co the khac nhe giua cac lan chay`,
        sep(),
      ]);
    },
    status() {
      const cpu = rand(15,85), ram = rand(30,75);
      const netIn = rand(10,500), netOut = rand(5,100);
      const cpuC = cpu > 70 ? c.red : cpu > 50 ? c.yellow : c.green;
      const ramC = ram > 70 ? c.red : ram > 50 ? c.yellow : c.green;
      return printLines([
        c.cyan('System Status — DDoS Lab Monitor'),
        sep(),
        `  ${c.dim('CPU Usage    :')} ${cpuC(cpu + '%')} ${cpu > 70 ? c.red('[CANH BAO]') : ''}`,
        `  ${c.dim('RAM Usage    :')} ${ramC(ram + '%')}`,
        `  ${c.dim('Network IN   :')} ${c.cyan(netIn + ' Mbps')}`,
        `  ${c.dim('Network OUT  :')} ${c.cyan(netOut + ' Mbps')}`,
        `  ${c.dim('Firewall     :')} ${c.green('ACTIVE')}`,
        `  ${c.dim('IDS Status   :')} ${c.green('MONITORING')}`,
        `  ${c.dim('SYN Cookie   :')} ${c.green('ENABLED')}`,
        `  ${c.dim('Rate Limiter :')} ${c.yellow('100 req/s per IP')}`,
        `  ${c.dim('Last Threat  :')} ${c.red('SYN Flood 192.168.x.1 — 2m ago')}`,
        `  ${c.dim('Uptime       :')} ${c.white(rand(1,99) + ' ngay ' + rand(0,23) + ' gio')}`,
        sep(),
      ]);
    },
    'syn-cookie'() {
      return printLines([
        c.green('SYN Cookie — Co che Chong SYN Flood'),
        sep(),
        `${c.cyan('Van de:')} Server cap slot bo nho ngay khi nhan SYN`,
        `  Bi SYN Flood: ${c.red('bo nho kiet, tu choi ket noi hop le')}`,
        '',
        `${c.cyan('Giai phap SYN Cookie:')}`,
        `  1. Client gui SYN → Server ${c.green('KHONG luu state')}`,
        `  2. Server tinh: cookie = hash(IP, port, seq, secret)`,
        `  3. Server gui SYN-ACK voi Seq = cookie`,
        `  4. Client gui ACK voi Ack = cookie+1`,
        `  5. Server verify → chi cap bo nho khi ACK hop le`,
        '',
        `  Attacker gui trieu SYN → ${c.green('Server khong ton bo nho')}`,
        `  Nguoi dung that → ${c.green('ket noi thanh cong')}`,
        sep(),
      ]);
    },
    ratelimit() {
      return printLines([
        c.green('Rate Limiting — Token Bucket Algorithm'),
        sep(),
        `${c.cyan('Rate Limiter:')} Gioi han so request/giay tu moi IP`,
        '',
        `${c.yellow('Token Bucket Algorithm:')}`,
        `  Moi IP co 1 xo (bucket) chua toi da ${c.green('100 token')}`,
        `  Moi giay: xo duoc nap them ${c.green('100 token')}`,
        `  Moi request tieu ton ${c.yellow('1 token')}`,
        `  Khi xo het token → ${c.red('429 Too Many Requests')}`,
        '',
        `${c.cyan('Vi du:')}`,
        `  Nguoi dung binh thuong: 2-5 req/s → ${c.green('khong bao gio can token')}`,
        `  Bot tan cong: 500 req/s → ${c.red('can token 0.2s → bi chan')}`,
        '',
        `${c.cyan('Adaptive Rate Limit:')} ML-IDS tu dong dieu chinh nguong real-time`,
        sep(),
      ]);
    },
    waf() {
      return printLines([
        c.green('WAF — Web Application Firewall'),
        sep(),
        `${c.cyan('WAF la gi?')} Lop bao ve chuyen biet cho ung dung web`,
        `  Phan tich noi dung HTTP request (URL, Header, Body, Cookie)`,
        '',
        `${c.yellow('3 Loai Rule WAF:')}`,
        '',
        `  ${c.cyan('1. Signature-based Rule')}`,
        `     So khop regex pattern voi database tan cong`,
        `     Chan SQL Injection: ?q='; DROP TABLE users;--`,
        `     Chan XSS: <script>alert(1)</script>`,
        '',
        `  ${c.cyan('2. Allowlist / Blocklist Rule')}`,
        `     Chi cho phep IP/Country trong whitelist`,
        `     Block IP trong threat intelligence feed`,
        '',
        `  ${c.cyan('3. ML-based Anomaly Rule')}`,
        `     Hoc hanh vi binh thuong → phat hien bat thuong`,
        `     Hieu qua voi ${c.green('HTTP Flood, bot traffic')}`,
        '',
        `${c.cyan('Nha cung cap:')} Cloudflare WAF, AWS WAF, ModSecurity`,
        sep(),
      ]);
    },
    history() {
      if (history.length === 0) return printLines([c.dim('Chua co lenh nao.')]);
      const lines = [c.cyan('Command History:'), sep()];
      history.slice(-10).forEach((cmd, i) => {
        lines.push(`  ${c.dim(String(i+1).padStart(3))}  ${c.white(cmd)}`);
      });
      lines.push(sep());
      return printLines(lines);
    },
    async matrix() {
      await printLine(c.green('Initializing Matrix protocol...'));
      for (let i = 0; i < 5; i++) {
        await new Promise(r => setTimeout(r, 250));
        let row = '';
        for (let j = 0; j < 60; j++) row += Math.random() > 0.5 ? '1' : '0';
        await printLine(`<span style="color:#00ff88;font-family:monospace;font-size:11px;letter-spacing:2px">${row}</span>`);
      }
      await new Promise(r => setTimeout(r, 400));
      await printLine(`<span style="color:#00ff88;font-size:16px;font-weight:700;letter-spacing:2px">Wake up, Neo...</span>`);
      await new Promise(r => setTimeout(r, 300));
      await printLine(`<span style="color:#00ff88;font-size:13px">The Matrix has you...</span>`);
      await printLine(sep());
    },
  };
  async function execute(raw) {
    const parts = raw.trim().split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1);
    printPromptLine(raw);
    if (!raw.trim()) return;
    if (history[history.length - 1] !== raw) history.push(raw);
    historyIdx = history.length;
    const handler = handlers[cmd];
    if (handler) {
      await handler(args);
    } else {
      await printLine(c.red(`-bash: '${cmd}': command not found. `) + c.dim("Go 'help' de xem danh sach."));
      await printLine(sep());
    }
    output.scrollTop = output.scrollHeight;
  }
  async function showWelcome() {
    const lines = [
      c.cyan('  ██████╗ ██████╗  ██████╗ ███████╗'),
      c.cyan('  ██╔══██╗██╔══██╗██╔═══██╗██╔════╝'),
      c.cyan('  ██║  ██║██║  ██║██║   ██║███████╗'),
      c.cyan('  ██║  ██║██║  ██║██║   ██║╚════██║'),
      c.cyan('  ██████╔╝██████╔╝╚██████╔╝███████║'),
      c.cyan('  ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝'),
      '',
      c.yellow('  DDoS Learning Hub Terminal v1.0'),
      c.dim('  Moi truong gia lap an toan — Chi danh cho giao duc'),
      '',
      c.white("  Go ") + c.green("'help'") + c.white(" de xem danh sach lenh."),
      c.dim("  Tab: autocomplete  |  Up/Down: lich su lenh"),
      sep(),
    ];
    for (let i = 0; i < lines.length; i++) {
      await printLine(lines[i], i * 35);
    }
  }
  function init() {
    output = document.getElementById('terminal-output');
    input = document.getElementById('terminal-input');
    form = document.getElementById('terminal-form');
    if (!output || !input || !form) return;
    form.addEventListener('submit', e => {
      e.preventDefault();
      const val = input.value.trim();
      input.value = '';
      if (val) execute(val);
    });
    input.addEventListener('keydown', e => {
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (historyIdx > 0) { historyIdx--; input.value = history[historyIdx] || ''; }
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIdx < history.length - 1) { historyIdx++; input.value = history[historyIdx] || ''; }
        else { historyIdx = history.length; input.value = ''; }
      }
      if (e.key === 'Tab') {
        e.preventDefault();
        const partial = input.value.trim().toLowerCase();
        if (!partial) return;
        const match = COMMANDS.find(x => x.startsWith(partial));
        if (match) input.value = match;
      }
    });
    document.getElementById('terminal-container')?.addEventListener('click', () => input.focus());
    showWelcome();
  }
  return { init };
})();
TerminalDemo.init();