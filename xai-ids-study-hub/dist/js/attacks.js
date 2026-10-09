/* attacks.js — Chương 07: Attack Atlas, 14 hoạt cảnh + dấu vết flow + số liệu thật */
(function(){
const W=900,H=330;
/* ---------- sinh packet đại diện cho một flow của từng loại ---------- */
const P_=(t,dir,len,flags)=>({t,dir,len,flags:flags||''});
const GEN=window.GEN={
 benign:()=>[[0,'f',60,'S'],[.06,'b',60,'SA'],[.09,'f',54,'A'],[.2,'f',517,'PA'],[.35,'b',1400,'PA'],[.6,'f',300,'PA'],[.9,'b',1400,'PA'],[1.2,'b',1400,'PA'],[1.8,'f',54,'A'],[2.1,'b',900,'PA'],[2.4,'f',54,'FA'],[2.45,'b',54,'FA']].map(x=>P_(...x)),
 flood:(n,dt,len,bwdN)=>{const a=[P_(0,'f',60,'S'),P_(dt,'b',60,'SA')];for(let i=0;i<n;i++)a.push(P_(2*dt+i*dt,'f',len,'PA'));for(let i=0;i<bwdN;i++)a.push(P_(3*dt+i*dt*3,'b',54,'A'));return a},
 udp:()=>Array.from({length:60},(_,i)=>P_(i*.004,'f',1024,'')),
 hulk:()=>{const a=[P_(0,'f',60,'S'),P_(.01,'b',60,'SA'),P_(.02,'f',54,'A')];for(let i=0;i<8;i++){a.push(P_(.05+i*.12,'f',420+i*37,'PA'));a.push(P_(.09+i*.12,'b',1400,'PA'))}a.push(P_(1.2,'f',54,'FA'));return a},
 golden:()=>{const a=[P_(0,'f',60,'S'),P_(.05,'b',60,'SA')];for(let i=0;i<10;i++){a.push(P_(.4+i*.45,'f',210,'PA'));a.push(P_(.45+i*.45,'b',1400,'PA'))}return a},
 slowloris:()=>[P_(0,'f',60,'S'),P_(.08,'b',60,'SA'),P_(.1,'f',54,'A'),P_(.2,'f',120,'PA'),P_(1.7,'f',58,'PA'),P_(3.2,'f',59,'PA'),P_(4.7,'f',58,'PA'),P_(6.2,'f',58,'PA'),P_(7.7,'f',57,'PA')],
 slowhttp:()=>[P_(0,'f',60,'S'),P_(.07,'b',60,'SA'),P_(.1,'f',54,'A'),P_(.3,'f',260,'PA'),P_(2.4,'f',55,'PA'),P_(4.8,'f',55,'PA'),P_(7.1,'f',55,'PA'),P_(9.4,'f',55,'PA'),P_(11.8,'f',55,'PA')],
 ftp:()=>[P_(0,'f',60,'S'),P_(.01,'b',60,'SA'),P_(.02,'f',54,'A'),P_(.05,'b',74,'PA'),P_(.12,'f',70,'PA'),P_(.14,'b',80,'PA'),P_(.2,'f',72,'PA'),P_(.45,'b',92,'PA'),P_(.5,'f',54,'R')],
 ssh:()=>{const a=[P_(0,'f',60,'S'),P_(.01,'b',60,'SA'),P_(.02,'f',54,'A')];for(let i=0;i<7;i++){a.push(P_(.05+i*.09,'f',140+i*40,'PA'));a.push(P_(.08+i*.09,'b',180+i*60,'PA'))}a.push(P_(.8,'b',100,'PA'));a.push(P_(1.2,'f',54,'R'));return a},
 webbrute:()=>{const a=[P_(0,'f',60,'S'),P_(.01,'b',60,'SA'),P_(.02,'f',54,'A')];for(let i=0;i<3;i++){a.push(P_(.1+i*.35,'f',320,'PA'));a.push(P_(.18+i*.35,'b',410,'PA'))}a.push(P_(1.3,'f',54,'FA'));a.push(P_(1.32,'b',54,'FA'));return a},
 sqli:()=>[P_(0,'f',60,'S'),P_(.03,'b',60,'SA'),P_(.04,'f',54,'A'),P_(.1,'f',470,'PA'),P_(.3,'b',1400,'PA'),P_(.33,'b',900,'PA'),P_(.4,'f',54,'A'),P_(.5,'f',54,'FA'),P_(.52,'b',54,'FA')],
 xss:()=>[P_(0,'f',60,'S'),P_(.03,'b',60,'SA'),P_(.04,'f',54,'A'),P_(.1,'f',610,'PA'),P_(.28,'b',1250,'PA'),P_(.4,'f',54,'A'),P_(.5,'f',54,'FA'),P_(.52,'b',54,'FA')],
 bot:()=>{const a=[P_(0,'f',60,'S'),P_(.04,'b',60,'SA'),P_(.05,'f',54,'A')];for(let i=0;i<6;i++){a.push(P_(1+i*2.0+(i%2?.03:-.02),'f',120,'PA'));a.push(P_(1.06+i*2.0,'b',90,'PA'))}return a},
 infil:()=>[P_(0,'f',60,'S'),P_(.002,'b',54,'R')]
};
const ATK=[
 {key:'DDOS attack-HOIC',kind:'flood',group:'ddos',port:'80/TCP',gen:()=>GEN.flood(60,.008,380,40).map(x=>x),
  cfg:{src:6,rate:150,label:'HTTP flood bằng nhiều “booster”',cap:90,size:380},
  summary:'HTTP flood cường độ cao từ nhiều nguồn, mỗi nguồn gửi request lặp lại dồn dập để làm cạn tài nguyên web server.',
  how:['Nhiều máy (hoặc nhiều luồng) cùng gửi HTTP request đến một URL.','HOIC dùng “booster” để xoay vòng header/URL nên khó chặn bằng chữ ký đơn giản.','Server tốn CPU/băng thông cho request giả, người dùng thật bị từ chối.'],
  signals:['Packets/s rất cao','Nhiều flow ngắn tới cùng đích :80','IAT rất nhỏ và đều'],
  blind:['Nội dung URL và header của từng request','Request nào là “thật”, request nào là “booster”'],
  extra:'Rate limiting, CDN/WAF chống DDoS, kiểm tra hành vi theo nguồn.',
  careful:'F1 gần 100% nhưng Top feature có Init Fwd Win Byts, Dst Port: dấu hiệu fingerprint môi trường chứ không chỉ hành vi.'},
 {key:'DDoS attacks-LOIC-HTTP',kind:'flood',group:'ddos',port:'80/TCP',gen:()=>GEN.flood(50,.005,130,20),
  cfg:{src:8,rate:130,label:'LOIC gửi HTTP request ồ ạt',cap:90,size:130},
  summary:'LOIC (Low Orbit Ion Cannon) tạo lượng lớn HTTP request từ nhiều máy để gây quá tải một mục tiêu.',
  how:['Nhiều máy chạy công cụ LOIC, cùng nhắm một server.','Mỗi máy gửi request liên tục, ít cần phản hồi.','Tổng tải từ nhiều nguồn vượt khả năng server.'],
  signals:['Fwd Pkts/s cao','Fwd IAT Std bất thường','Nhiều flow cùng đích'],
  blind:['Danh tính thật của botnet/tình nguyện viên','Nội dung request'],
  extra:'Chặn theo nguồn, anycast/scrubbing, giới hạn kết nối.',
  careful:'Jaccard@5 SHAP–LIME thấp (≈0,10): hai phương pháp chọn khá khác feature cho lớp này, nên đọc riêng từng explainer.'},
 {key:'DDOS attack-LOIC-UDP',kind:'udp',group:'ddos',port:'UDP',gen:GEN.udp,
  cfg:{src:6,rate:220,label:'UDP flood: không cần bắt tay',cap:100,size:1024},
  summary:'Gửi rất nhiều datagram UDP vào mục tiêu để chiếm băng thông và tài nguyên xử lý, không cần bắt tay TCP.',
  how:['Kẻ tấn công gửi UDP lớn, tốc độ cao.','Không có SYN/ACK nên chỉ thấy luồng một chiều.','Băng thông và CPU xử lý gói bị chiếm.'],
  signals:['Protocol = UDP','Packet rate rất cao, một chiều','Ít hoặc không có packet về'],
  blind:['Nội dung datagram (có thể ngẫu nhiên)'],
  extra:'Lọc UDP không cần thiết ở biên, giới hạn băng thông theo nguồn.',
  careful:'Chỉ 346 flow test: độ chắc chắn theo lớp thấp hơn các lớp DDoS khác; 12 flow bị nhầm sang LOIC-HTTP.'},
 {key:'DoS attacks-Hulk',kind:'flood',group:'dos',port:'80/TCP',gen:GEN.hulk,
  cfg:{src:1,rate:100,label:'Hulk: URL ngẫu nhiên để né cache',cap:80,size:520,urls:true},
  summary:'HTTP Unbearable Load King: mỗi request mang URL/tham số khác nhau để vượt cache, buộc server tự xử lý mọi request.',
  how:['Mỗi request có tham số ngẫu nhiên (ví dụ ?q=a8f3k2).','Cache/CDN không trả lời được nên request đi thẳng tới server.','Server phải xử lý hàng nghìn request “độc nhất”.'],
  signals:['HTTP request rate cao','Packet size biến đổi nhẹ','Phản hồi server đều lớn'],
  blind:['URL/tham số ngẫu nhiên (thứ làm nên bản chất Hulk)'],
  extra:'WAF phát hiện mẫu URL bất thường, tách cache theo chuẩn hóa query.',
  careful:'Hiệu năng rất cao nhưng Domain Precision@5 còn thấp (SHAP ≈0,2, bản tri thức rộng): mô hình đúng nhưng chỉ một phần nhờ “tín hiệu chuyên gia mong đợi”.'},
 {key:'DoS attacks-GoldenEye',kind:'flood',group:'dos',port:'80/TCP',gen:GEN.golden,
  cfg:{src:3,rate:55,label:'GoldenEye: giữ kết nối + request liên tục',cap:80,size:210,keepalive:true},
  summary:'HTTP DoS duy trì nhiều kết nối keep-alive và gửi request lặp lại để làm cạn tài nguyên web server.',
  how:['Mở nhiều kết nối HTTP keep-alive.','Gửi request đều đặn trên mỗi kết nối, kèm header ngẫu nhiên.','Server giữ kết nối và tốn CPU phục vụ.'],
  signals:['Nhiều kết nối HTTP kéo dài','Thời lượng/IAT bất thường','Packet response biến động'],
  blind:['Header ngẫu nhiên trong từng request'],
  extra:'Giới hạn kết nối đồng thời và request/kết nối.',
  careful:'Top feature toàn cục cần đối chiếu cơ chế thay vì mặc định coi là bằng chứng tấn công.'},
 {key:'DoS attacks-Slowloris',kind:'slow',group:'dos',port:'80/TCP',gen:GEN.slowloris,
  cfg:{pool:100,openRate:6,gap:1.6,label:'Slowloris: header gửi chưa xong',mode:'header'},
  summary:'Giữ thật nhiều kết nối HTTP mở bằng cách gửi header chưa hoàn chỉnh, từng mẩu thật chậm.',
  how:['Mở rất nhiều kết nối tới server.','Mỗi kết nối gửi một ít header (ví dụ “X-a: b”) rồi chờ.','Server cứ chờ header kết thúc, bể kết nối đầy dần.'],
  signals:['Flow kéo dài','Packet nhỏ và thưa','Nhiều socket mở đồng thời','Băng thông thấp'],
  blind:['Header đang được gửi dang dở','Số socket server thực sự còn trống'],
  extra:'Timeout header ngắn, giới hạn kết nối theo IP, reverse proxy buffer request.',
  careful:'Flow feature thấy được nhịp chậm nhưng không thấy trực tiếp nội dung header.'},
 {key:'DoS attacks-SlowHTTPTest',kind:'slow',group:'dos',port:'80/TCP',gen:GEN.slowhttp,
  cfg:{pool:100,openRate:4,gap:2.4,label:'SlowHTTPTest: body/header chậm',mode:'body',variants:true},
  summary:'Công cụ kiểm thử gửi header hoặc body HTTP rất chậm (hoặc đọc phản hồi chậm) để server phải chờ và giữ tài nguyên.',
  how:['Chọn một kiểu: slow headers, slow body (Content-Length lớn, gửi từng byte), hoặc slow read.','Giữ kết nối mở càng lâu càng tốt.','Pool kết nối của server bị chiếm.'],
  signals:['Flow Duration rất dài','Tốc độ rất thấp','IAT lớn'],
  blind:['Kiểu chậm nào đang dùng (header, body hay read)'],
  extra:'Giới hạn thời gian đọc body, giới hạn kết nối theo IP.',
  careful:'Recall chỉ 37,64% và 1.082 flow bị đoán là FTP-BruteForce: nhịp chậm giống nhau khiến hai lớp bị lẫn.'},
 {key:'FTP-BruteForce',kind:'brute',group:'brute',port:'21/TCP',gen:GEN.ftp,
  cfg:{port:'21',service:'FTP',interval:.45,user:'admin',label:'Thử hàng loạt mật khẩu FTP'},
  summary:'Thử nhiều tổ hợp tài khoản/mật khẩu qua dịch vụ FTP, thường ở cổng 21.',
  how:['Mở kết nối FTP, gửi USER/PASS.','Server trả “530 Login incorrect”.','Đóng/RST và lặp lại với mật khẩu khác.'],
  signals:['Nhiều phiên ngắn lặp lại','Đích cổng 21','RST/kết thúc đột ngột'],
  blind:['Tên đăng nhập và mật khẩu đang thử','Phiên nào thành công'],
  extra:'Khóa tài khoản/IP sau N lần sai, fail2ban, log xác thực.',
  careful:'IDS flow chỉ học nhịp kết nối; 305 flow FTP bị đoán nhầm sang SlowHTTPTest.'},
 {key:'SSH-Bruteforce',kind:'brute',group:'brute',port:'22/TCP',gen:GEN.ssh,
  cfg:{port:'22',service:'SSH',interval:.35,user:'root',label:'Thử hàng loạt mật khẩu SSH'},
  summary:'Thử đăng nhập SSH lặp lại để đoán thông tin xác thực. Kênh SSH được mã hóa nên chỉ thấy nhịp kết nối.',
  how:['Bắt tay SSH, trao đổi khóa.','Gửi mật khẩu thử qua kênh đã mã hóa.','Bị từ chối, đóng kết nối, thử lại.'],
  signals:['Đích cổng 22','Phiên ngắn lặp lại','Nhịp thử đều'],
  blind:['Toàn bộ nội dung (đã mã hóa)'],
  extra:'Khóa theo IP, bắt buộc xác thực khóa công khai, MFA.',
  careful:'Kết quả rất tốt trên dataset nhưng Dst Port là feature dễ mang tính môi trường.'},
 {key:'Brute Force -Web',kind:'brute',group:'brute',port:'80/TCP',gen:GEN.webbrute,
  cfg:{port:'80',service:'HTTP /login',interval:.55,user:'admin',label:'Thử mật khẩu trên form đăng nhập web'},
  summary:'Thử đăng nhập lặp lại trên biểu mẫu hoặc endpoint web.',
  how:['Gửi POST /login với mật khẩu khác nhau.','Server trả trang “sai mật khẩu” có kích thước gần như nhau.','Lặp lại hàng trăm lần.'],
  signals:['Nhiều request POST giống nhau','Phản hồi kích thước gần bằng nhau','Nhiều lần xác thực'],
  blind:['Nội dung form (tên/mật khẩu)','Mã phản hồi 200/302/401'],
  extra:'CAPTCHA, rate limit theo tài khoản, WAF.',
  careful:'Chỉ 122 flow test; không nên đưa kết luận thống kê mạnh.'},
 {key:'Brute Force -XSS',kind:'payload',group:'web',port:'80/TCP',gen:GEN.xss,
  cfg:{type:'xss',req:'GET /search?q=<mark>&lt;script&gt;alert(1)&lt;/script&gt;</mark> HTTP/1.1',resp:'Trang phản hồi chứa nguyên đoạn script: trình duyệt nạn nhân sẽ chạy nó',label:'XSS: chèn mã script qua input'},
  summary:'Nhãn web attack liên quan các thử nghiệm XSS; flow feature chỉ thấy dấu hiệu gián tiếp.',
  how:['Gửi input chứa mã script.','Ứng dụng phản chiếu input vào trang không lọc.','Trình duyệt nạn nhân chạy script.'],
  signals:['Request dài bất thường','Nhiều request thử nghiệm','Phản hồi khá lớn'],
  blind:['Chuỗi &lt;script&gt; trong URL/body','Trang phản hồi có chứa script hay không'],
  extra:'WAF với quy tắc XSS, mã hóa output, Content-Security-Policy.',
  careful:'Chỉ 46 flow test; cần WAF/payload inspection để xác minh XSS.'},
 {key:'SQL Injection',kind:'payload',group:'web',port:'80/TCP',gen:GEN.sqli,
  cfg:{type:'sqli',req:"GET /product?id=1<mark> OR 1=1 --</mark> HTTP/1.1",resp:'Truy vấn trả về toàn bộ bảng thay vì một sản phẩm',label:'SQL Injection: chèn câu lệnh SQL'},
  summary:'Chèn câu lệnh SQL qua input của ứng dụng để đọc hoặc thay đổi dữ liệu.',
  how:['Chèn điều kiện luôn đúng (OR 1=1) vào tham số.','Câu SQL bị đổi nghĩa.','Cơ sở dữ liệu trả nhiều dữ liệu hơn dự kiến.'],
  signals:['Request dài bất thường','Phản hồi lớn hơn thường lệ','Truy cập endpoint động'],
  blind:['Câu SQL trong tham số','Dữ liệu bị lấy ra'],
  extra:'WAF/DPI, prepared statement, giám sát truy vấn cơ sở dữ liệu.',
  careful:'Chỉ 17 flow test và 9 flow trong cohort; 78 feature không đọc trực tiếp payload SQL.'},
 {key:'Bot',kind:'bot',group:'other',port:'nhiều cổng',gen:GEN.bot,
  cfg:{period:2.0,jitter:.03,label:'Bot “gọi về nhà” theo chu kỳ'},
  summary:'Máy bị điều khiển tạo traffic tự động, liên lạc định kỳ với hạ tầng C2 (beaconing).',
  how:['Máy bị nhiễm kết nối C2 theo chu kỳ cố định.','Gửi trạng thái, nhận lệnh.','Nhịp rất đều khác với người dùng thật.'],
  signals:['Beaconing định kỳ','IAT Std nhỏ','Packet size gần như không đổi'],
  blind:['Nội dung lệnh C2 (thường mã hóa)'],
  extra:'Phân tích DNS/C2, danh sách IP độc hại, EDR trên máy.',
  careful:'Jaccard SHAP–LIME thấp ở mọi k, nhưng SHAP gần như hoàn toàn dựa vào Dst Port (mean|φ|≈7,4, gấp ~90 lần feature thứ 2), cần kiểm tra tính tổng quát trên mạng mới.'},
 {key:'Infilteration',kind:'infil',group:'other',port:'nhiều cổng nội bộ',gen:GEN.infil,
  cfg:{interval:.9,label:'Kẻ tấn công đã ở bên trong, dò các máy khác'},
  summary:'Kẻ tấn công đã xâm nhập và hoạt động bên trong mạng (quét nội bộ, di chuyển ngang); hành vi rất đa dạng.',
  how:['Chiếm một máy trong mạng (foothold).','Quét/kết nối tới nhiều máy nội bộ khác.','Thu thập và gom dữ liệu.'],
  signals:['Kết nối nội bộ bất thường','Truy cập nhiều tài nguyên','Mẫu không đồng nhất'],
  blind:['Mục đích của từng kết nối nội bộ','Máy nào là “foothold”'],
  extra:'Phân đoạn mạng, giám sát di chuyển ngang, EDR, UEBA.',
  careful:'Recall 15,98%: 12.026 flow Infilteration bị đoán là Benign. Đây là lớp đa dạng và khó nhất.'}
];
HUB.ATK=ATK;
const BEN=()=>HUB.computeFeatures(GEN.benign());
const lvl=f1=>f1>=.99?['Rất tốt','good']:f1>=.9?['Tốt','good']:f1>=.75?['Khá','mid']:f1>=.5?['Khó','mid']:['Rất khó','bad'];
const groupName={ddos:'DDOS',dos:'DOS',brute:'BRUTE FORCE',web:'WEB',other:'KHÁC'};

/* ---------- Scene ---------- */
class Scene{
 constructor(cv,atk){this.cv=cv;this.a=atk;this.ctx=cv.getContext('2d');const dpr=Math.min(2,devicePixelRatio||1);cv.width=W*dpr;cv.height=H*dpr;this.ctx.scale(dpr,dpr);this.speed=1;this.playing=true;this.reset()}
 reset(){this.t=0;this.parts=[];this.acc=0;this.cpu=0;this.bw=0;this.served=0;this.denied=0;this.legitT=0;this.sockets=0;this.attempts=0;this.rst=0;this.log=[];this.touched=new Set([0]);this.nextT=0;this.beacons=[];this.users=[];this.bNext=1;this.uNext=1.5;this.phase=0;this.typed=0;this.rr=rng(7);this.mode=this.a.cfg.mode||''}
 P(x0,y0,x1,y1,sp,col,r,kind){this.parts.push({x0,y0,x1,y1,u:0,sp,col,r:r||3,kind})}
 srcPos(i,n){return[100,n===1?H/2-20:50+(H-140)*i/(n-1)]}
 get srv(){return{x:690,y:H/2-20,w:150,h:150}}
 step(dt){if(!this.playing)return;dt*=this.speed;this.t+=dt;const c=this.a.cfg,s=this.srv;const K=this.a.kind;
  if(K==='flood'||K==='udp'){const rate=c.rate;this.acc+=rate*dt*.5;while(this.acc>=1){this.acc--;if(this.parts.length<260){const i=Math.floor(this.rr()*c.src);const[x,y]=this.srcPos(i,c.src);this.P(x+20,y,s.x,s.y+s.h/2+(this.rr()-.5)*60,1.4+this.rr()*.6,K==='udp'?'#ffb020':'#ff7c43',2.5)}}
   const tgt=clamp(rate/c.cap,0,1.1);this.cpu+=(tgt-this.cpu)*dt*1.8;this.bw=clamp(rate*(c.size||300)/(c.cap*600),0,1)}
  if(K==='slow'){this.acc+=c.openRate*dt;while(this.acc>=1&&this.sockets<c.pool){this.acc--;this.sockets++}
   const dr=this.sockets/c.gap;this.acc2=(this.acc2||0)+dr*dt*.35;while(this.acc2>=1){this.acc2--;const i=Math.floor(this.rr()*3);const[x,y]=this.srcPos(i,3);this.P(x+20,y,s.x,s.y+30+this.rr()*90,.9,'#ffb020',2)}
   this.cpu+=(clamp(this.sockets/c.pool*.18,0,1)-this.cpu)*dt;this.bw=clamp(this.sockets/c.gap*60/8000,0,1)}
  if(K==='brute'){this.nextT-=dt;if(this.nextT<=0){this.nextT=c.interval;const[x,y]=this.srcPos(0,1);this.P(x+20,y,s.x,s.y+s.h/2,1.8,'#ff7c43',4,'att');this.attempts++;const pw=['123456','password','qwerty','letmein','admin','dragon','welcome','111111','abc123','monkey'][this.attempts%10];this.log.unshift(`${c.user}:${pw}`);if(this.log.length>6)this.log.pop()}
   this.cpu+=(clamp(.12+this.attempts%7*.01,0,.3)-this.cpu)*dt;this.bw=.04}
  if(K==='infil'){this.nextT-=dt;if(this.nextT<=0){this.nextT=c.interval;const n=this.ring().length;const tgt=1+Math.floor(this.rr()*(n-1));const a=this.ring()[0],b=this.ring()[tgt];this.P(a[0],a[1],b[0],b[1],1.3,'#ff7c43',4,'inf'+tgt)}}
  if(K==='bot'){this.bNext-=dt;this.uNext-=dt;if(this.bNext<=0){this.bNext=c.period*(1+(this.rr()-.5)*2*c.jitter);this.beacons.push(this.t);this.P(110,95,690,95,1.2,'#ff7c43',4)}
   if(this.uNext<=0){this.uNext=-Math.log(1-this.rr())*2.0;this.users.push(this.t);this.P(110,250,690,250,1.2,'#6aa51a',4)}}
  if(K==='payload'){this.phase+=dt;const cyc=9;const ph=this.phase%cyc;if(ph<.05&&!this._sent){this._sent=1;this.P(110,H/2-20,690,H/2-20,.7,'#ff7c43',9,'pay')}if(ph>.1)this._sent=0;this.typed=clamp(ph/3,0,1)}
  // legit user
  if(K==='flood'||K==='udp'||K==='slow'||K==='brute'){this.legitT-=dt;if(this.legitT<=0){this.legitT=K==='brute'?7:1.2;this.P(100,H-60,s.x,s.y+s.h-20,1.5,'#6aa51a',4,'legit')}}
  for(const p of this.parts){p.u+=dt*p.sp;if(p.u>=1&&!p.done){p.done=1;this.arrive(p)}}
  this.parts=this.parts.filter(p=>!p.done||p.back&&p.u<1.0);
 }
 ring(){const cx=500,cy=H/2,r=110;return Array.from({length:9},(_,i)=>i===0?[cx-r-10,cy]:[cx+Math.cos((i-1)/8*Math.PI*2)*r*0.95+30,cy+Math.sin((i-1)/8*Math.PI*2)*r*.95])}
 arrive(p){const K=this.a.kind,s=this.srv;
  if(p.kind==='legit'){const ok=(K==='slow'?this.sockets<this.a.cfg.pool:this.cpu<.95);if(ok)this.served++;else this.denied++;this.parts.push({x0:p.x1,y0:p.y1,x1:p.x0,y1:p.y0,u:0,sp:1.5,col:ok?'#6aa51a':'#e5484d',r:4,back:1})}
  if(p.kind==='att'){this.rst++;this.parts.push({x0:p.x1,y0:p.y1,x1:p.x0,y1:p.y0,u:0,sp:1.8,col:'#e5484d',r:4,back:1,x:'✗'})}
  if(p.kind&&p.kind.startsWith('inf')){this.touched.add(+p.kind.slice(3))}}
 meters(){const K=this.a.kind,c=this.a.cfg,m=[];
  if(K==='flood'||K==='udp'){m.push(['CPU server',this.cpu,vi(this.cpu*100,0)+'%']);m.push(['Băng thông',this.bw,vi(this.bw*100,0)+'%']);m.push(['Người dùng thật được phục vụ',this.served+this.denied?this.served/(this.served+this.denied):1,`${this.served} ✓ / ${this.denied} ✗`]);m.push(['Nguồn tấn công',c.src/8,c.src+' nguồn'])}
  if(K==='slow'){m.push(['Kết nối bị chiếm',this.sockets/c.pool,`${this.sockets}/${c.pool}`]);m.push(['CPU server',this.cpu,vi(this.cpu*100,0)+'%']);m.push(['Băng thông (rất thấp)',this.bw,vi(this.bw*100,1)+'%']);m.push(['Người dùng thật được phục vụ',this.served+this.denied?this.served/(this.served+this.denied):1,`${this.served} ✓ / ${this.denied} ✗`])}
  if(K==='brute'){m.push(['Số lần thử',clamp(this.attempts/200,0,1),String(this.attempts)]);m.push(['Tốc độ thử (/phút)',clamp(60/c.interval/400,0,1),Math.round(60/c.interval)+'/phút']);m.push(['RST / thất bại',this.attempts?this.rst/this.attempts:0,String(this.rst)]);m.push(['CPU server',this.cpu,vi(this.cpu*100,0)+'%'])}
  if(K==='infil'){m.push(['Máy nội bộ bị chạm',this.touched.size/9,`${this.touched.size}/9`]);m.push(['Kết nối ngang',clamp(this.t/c.interval/40,0,1),String(Math.floor(this.t/c.interval))]);m.push(['Băng thông ngoài',.04,'thấp']);m.push(['Cảnh báo ở biên',0,'0 (đã ở trong)'])}
  if(K==='bot'){const iat=a=>{const r=[];for(let i=1;i<a.length;i++)r.push(a[i]-a[i-1]);return r};const bs=std(iat(this.beacons)),us=std(iat(this.users));m.push(['IAT Std của bot (s)',clamp(bs/3,0,1),vi(bs,2)]);m.push(['IAT Std người dùng (s)',clamp(us/3,0,1),vi(us,2)]);m.push(['Số beacon',clamp(this.beacons.length/30,0,1),String(this.beacons.length)]);m.push(['Chu kỳ bot',c.period/10,vi(c.period,1)+' s'])}
  if(K==='payload'){m.push(['Kích thước request',.5,'~470 byte (thường)']);m.push(['Packet/s',.05,'thấp']);m.push(['Thời lượng flow',.1,'<1 s']);m.push(['Cờ RST',0,'0'])}
  return m}
 caption(){const K=this.a.kind,c=this.a.cfg;
  if(K==='flood')return this.cpu>.95?`<b>Server quá tải:</b> CPU ${vi(this.cpu*100,0)}%, người dùng thật bị từ chối (${this.denied} lần). ${c.urls?'Mỗi request mang URL khác nhau nên cache không giúp được gì.':''}`:`Các nguồn gửi ${c.rate} request/s (đơn vị minh họa). Server còn đáp ứng được nhưng CPU đang tăng ${c.keepalive?'(mỗi nguồn giữ nhiều kết nối keep-alive)':''}.`;
  if(K==='udp')return `Datagram UDP đi một chiều, không có bắt tay. Băng thông ${vi(this.bw*100,0)}% bị chiếm, ${this.denied?'người dùng thật bắt đầu bị từ chối.':'server sắp nghẹt.'}`;
  if(K==='slow'){const v=this.mode;return this.sockets>=c.pool?`<b>Pool kết nối đã đầy (${c.pool}/${c.pool}):</b> người dùng thật bị từ chối dù băng thông chỉ ~${vi(this.bw*100,1)}%. Đây là điểm khác với flood.`:`Mỗi kết nối chỉ gửi vài byte mỗi ${c.gap} giây (${v==='header'?'header HTTP dang dở':v==='body'?'từng byte của body':'đọc phản hồi rất chậm'}). Đã chiếm ${this.sockets}/${c.pool} kết nối.`}
  if(K==='brute')return `Mỗi lần thử là một kết nối ngắn tới cổng ${c.port}, thất bại rồi đóng bằng RST. Hệ thống chỉ thấy <b>nhịp</b> ${this.attempts} kết nối, không thấy mật khẩu (mờ ở bảng bên trái).`;
  if(K==='infil')return `Từ một máy đã bị chiếm, kẻ tấn công dò dần các máy nội bộ khác (${this.touched.size}/9 máy đã bị chạm). Traffic nằm bên trong mạng nên IDS ở biên khó thấy.`;
  if(K==='bot')return `Bot gọi về C2 mỗi ~${vi(c.period,1)} s rất đều (hàng trên), trong khi người dùng thật gửi request lúc nhanh lúc chậm (hàng dưới). Chính <b>độ đều</b> làm IAT Std của bot nhỏ.`;
  if(K==='payload')return this.a.cfg.type==='sqli'?'Gói tin có kích thước và nhịp trông như một request web bình thường. Chỉ nội dung (payload) mới lộ ra tấn công, mà 78 feature không đọc được.':'Request XSS dài hơn thường một chút nhưng về hình dạng flow vẫn rất giống traffic web.'}
 draw(){const x=this.ctx,K=this.a.kind,c=this.a.cfg,s=this.srv;x.clearRect(0,0,W,H);x.fillStyle='#0d1525';x.fillRect(0,0,W,H);
  x.font='10px DM Mono, monospace';x.textAlign='center';
  const box=(bx,by,bw,bh,fill,stroke,r=12)=>{x.beginPath();x.roundRect(bx,by,bw,bh,r);x.fillStyle=fill;x.fill();x.strokeStyle=stroke;x.lineWidth=1.5;x.stroke()};
  if(K==='infil'){const R=this.ring();R.forEach((p,i)=>{if(i>0){x.strokeStyle=this.touched.has(i)?'#ff7c4388':'#2c3a52';x.lineWidth=1;x.beginPath();x.moveTo(R[0][0],R[0][1]);x.lineTo(p[0],p[1]);x.stroke()}});
   R.forEach((p,i)=>{const hot=this.touched.has(i);box(p[0]-26,p[1]-16,52,32,hot?'#3a1d12':'#162137',hot?'#ff7c43':'#33425c',8);x.fillStyle=hot?'#ffb98f':'#9ba7b9';x.fillText(i===0?'foothold':['','Web','DB','Mail','File','HR','Dev','AD','Printer'][i],p[0],p[1]+4)});
   x.fillStyle='#8e9ab0';x.textAlign='left';x.fillText('MẠNG NỘI BỘ',360,26);x.fillStyle='#ff7c43';x.fillText('● máy bị chiếm / bị chạm',360,44)}
  else if(K==='bot'){x.fillStyle='#8e9ab0';x.textAlign='left';x.fillText('BOT (máy bị nhiễm) → C2',20,40);x.fillText('NGƯỜI DÙNG THẬT → Web',20,196);
   const lane=(ev,y,col)=>{x.strokeStyle='#2c3a52';x.beginPath();x.moveTo(20,y);x.lineTo(880,y);x.stroke();ev.forEach(tm=>{const px=880-(this.t-tm)*38;if(px>20){x.fillStyle=col;x.fillRect(px-1.5,y-18,3,36)}})};lane(this.beacons,95,'#ff7c43');lane(this.users,250,'#6aa51a');
   x.fillStyle='#5f6c82';x.textAlign='center';x.fillText('← thời gian trôi (khoảng 22 giây)',450,320)}
  else if(K==='payload'){box(60,H/2-50,120,80,'#162137','#33425c');x.fillStyle='#dfe6f1';x.fillText('Kẻ tấn công',120,H/2-6);box(s.x,s.y,s.w,s.h,'#162137',this.a.cfg.type==='sqli'?'#ff7c43':'#16b8b6');x.fillText(this.a.cfg.type==='sqli'?'Web + Database':'Web server',s.x+s.w/2,s.y+22);
   const req=this.a.cfg.req.replace(/<mark>|<\/mark>/g,'').replace(/&lt;/g,'<').replace(/&gt;/g,'>');const n=Math.floor(req.length*this.typed);x.textAlign='left';x.fillStyle='#0b1020';x.fillRect(30,H-100,840,60);x.fillStyle='#e9eef7';x.font='12px DM Mono, monospace';x.fillText(req.slice(0,n)+(this.typed<1?'▌':''),44,H-64);x.font='10px DM Mono, monospace';x.fillStyle='#8e9ab0';x.fillText('Nội dung HTTP request (payload)',44,H-84);x.textAlign='center'}
  else{ // flood / udp / slow / brute
   const n=K==='slow'?3:(K==='brute'?1:c.src);for(let i=0;i<n;i++){const[px,py]=this.srcPos(i,n);box(px-40,py-16,80,32,'#2a1a14','#ff7c43',8);x.fillStyle='#ffb98f';x.fillText(K==='brute'?'Kẻ tấn công':'Nguồn '+(i+1),px,py+4)}
   box(60,H-76,80,32,'#102418','#6aa51a',8);x.fillStyle='#9be3a0';x.fillText('Người dùng',100,H-56);
   const sc=this.cpu>.95||(K==='slow'&&this.sockets>=c.pool)?'#e5484d':'#16b8b6';box(s.x,s.y,s.w,s.h,'#162137',sc);x.fillStyle='#dfe6f1';x.fillText('Server',s.x+s.w/2,s.y+18);
   if(K==='slow'){const cols=20,rows=5,cw=(s.w-20)/cols,chh=14;for(let i=0;i<c.pool;i++){const cx=s.x+10+(i%cols)*cw,cy=s.y+34+Math.floor(i/cols)*chh;x.fillStyle=i<this.sockets?'#ff7c43':'#26344d';x.fillRect(cx,cy,cw-2,chh-3)}x.fillStyle='#9ba7b9';x.fillText('pool kết nối',s.x+s.w/2,s.y+s.h-8)}
   else{x.fillStyle='#26344d';x.fillRect(s.x+14,s.y+s.h-30,s.w-28,10);x.fillStyle=this.cpu>.95?'#e5484d':'#29d3d1';x.fillRect(s.x+14,s.y+s.h-30,(s.w-28)*clamp(this.cpu,0,1),10);x.fillStyle='#9ba7b9';x.fillText('CPU',s.x+s.w/2,s.y+s.h-36)}
   if(K==='brute'){x.textAlign='left';x.fillStyle='#8e9ab0';x.fillText('Thông tin đăng nhập đang thử (flow KHÔNG thấy):',20,36);this.log.forEach((l,i)=>{x.fillStyle=`rgba(255,184,143,${.9-i*.13})`;x.filter='blur(3px)';x.fillText(l,20,56+i*16);x.filter='none'});x.textAlign='center';x.fillStyle='#ffb98f';x.fillText(`cổng ${c.port} · ${c.service}`,s.x+s.w/2,s.y-8)}
   if(K==='flood'&&c.urls){x.textAlign='left';x.fillStyle='#8e9ab0';x.fillText('Mỗi request một URL khác (cache vô dụng):',20,26);for(let i=0;i<5;i++){const r=Math.floor((this.t*6+i*7919)%100000);x.fillStyle=`rgba(255,184,143,${.9-i*.14})`;x.fillText('GET /?q='+r.toString(36).padStart(5,'x'),20,46+i*15)}x.textAlign='center'}}
  // particles
  for(const p of this.parts){const u=clamp(p.u,0,1);const px=p.x0+(p.x1-p.x0)*u,py=p.y0+(p.y1-p.y0)*u;x.fillStyle=p.col;if(p.kind==='pay'){x.fillRect(px-14,py-9,28,18);x.fillStyle='#fff';x.fillText('GET',px,py+3)}else{x.beginPath();x.arc(px,py,p.r,0,6.3);x.fill();if(p.x){x.fillStyle='#fff';x.fillText(p.x,px,py-8)}}}
  x.textAlign='left';x.fillStyle='#5f6c82';x.fillText('t = '+vi(this.t,1)+' s',W-70,H-8);
 }
}

/* ---------- UI ---------- */
function cardHtml(a,i){const c=cls(a.key);const l=lvl(c.f1);const bins=Array.from({length:14},()=>0);const pk=a.gen();const tm=Math.max(...pk.map(x=>x.t))||1;pk.forEach(p=>bins[Math.min(13,Math.floor(p.t/tm*14))]++);
  return `<button class="attack-card" data-i="${i}"><div class="attack-top"><span class="tag">${groupName[a.group]}</span><span class="lvl ${l[1]}">${l[0]}</span></div><h3>${SHORT[a.key]}</h3><p>${a.cfg.label}.</p>${spark(bins,200,34,'#ff7c43')}<span class="f1">F1 <b>${(c.f1*100).toFixed(1)}%</b> · ${vi0(c.support)} flow test${c.support<200?' · lớp hiếm':''}</span><span class="go">▶ Xem hoạt cảnh + số liệu thật</span></button>`}
let cur=null,scene=null,raf=0,lastTs=0;
function openAttack(name,tab){const i=ATK.findIndex(a=>a.key===name);if(i<0)return;showAttack(i,tab)}
HUB.openAttack=openAttack;
function showAttack(i,tab){const a=ATK[i],c=cls(a.key);cur=a;const l=lvl(c.f1);
  const feat=HUB.computeFeatures(a.gen()),ben=BEN();const dstPort=a.port;
  const rows=[['Flow Duration (s)',feat.dur,ben.dur,vi],['Packets/s',feat.pps,ben.pps,vi0],['Flow IAT Mean (s)',feat.iatMean,ben.iatMean,v=>vi(v,4)],['Flow IAT Max (s)',feat.iatMax,ben.iatMax,v=>vi(v,3)],['Fwd Pkt Len Mean',feat.fLenMean,ben.fLenMean,v=>vi(v,0)],['Tổng packet',feat.n,ben.n,vi0],['RST Flag Count',feat.rst,ben.rst,vi0]];
  const cmp=rows.map(([n,v,b,f])=>{const mx=Math.max(v,b,1e-9);const sc=x=>x<=0?0:Math.max(.04,Math.log10(1+x/mx*99)/2);return `<div class="cmp-row"><span>${n}</span><span class="bar"><i style="width:${sc(v)*100}%"></i></span><span class="bar b"><i style="width:${sc(b)*100}%"></i></span><span class="n">${f(v)} <small style="color:#9aa5b8">/ ${f(b)}</small></span></div>`}).join('');
  // lỗi nhầm
  const ci=P.classOrder.indexOf(a.key),conf=P.cm[ci].map((v,j)=>[v,j]).filter(([v,j])=>j!==ci&&v>0).sort((x,y)=>y[0]-x[0]).slice(0,3),tot=P.cm[ci].reduce((s,x)=>s+x,0);
  // SHAP toàn cục
  let shapHtml='<p class="note">Chưa có dữ liệu SHAP toàn cục cho lớp này.</p>',ins='';
  if(c.globalPos){const mx=Math.max(...c.globalPos.map(x=>Math.abs(x[1])),1e-9);const sum=c.globalPos.reduce((s,x)=>s+Math.abs(x[1]),0);
    shapHtml=c.globalPos.map(([n,v],k)=>`<div class="cmp-row" style="grid-template-columns:150px 1fr 70px"><span>${k+1}. ${n}</span><span class="bar"><i style="width:${Math.max(3,Math.abs(v)/mx*100)}%;background:#16b8b6"></i></span><span class="n">+${vi(v,3)}</span></div>`).join('');
    const share=Math.abs(c.globalPos[0][1])/sum;ins=share>.6?`<div class="note warn"><b>${c.globalPos[0][0]}</b> chiếm ${pct(share,0)} tổng đóng góp của Top-5. Một feature đơn lẻ gánh gần hết điểm: dấu hiệu mô hình dựa vào fingerprint môi trường, cần kiểm chứng trên traffic mới.</div>`:''}
  const dom=c.domainSignals||[];const top=c.globalPos?c.globalPos.map(x=>x[0]):[];
  const domHtml=dom.length?`<p><b>Tín hiệu miền kỳ vọng:</b> ${dom.map(d=>`<span class="tagpill ${top.includes(d)?'hit':''}">${d}</span>`).join('')}</p>${top.length?`<p><b>Top-5 SHAP toàn cục:</b> ${top.map(d=>`<span class="tagpill ${dom.includes(d)?'hit':'miss'}">${d}</span>`).join('')}</p><p class="note">Xanh = trùng tín hiệu miền, cam = không trùng. Trùng ${top.filter(d=>dom.includes(d)).length}/5.</p>`:''}`:'<p class="note">Không có bảng tín hiệu miền cho lớp này.</p>';
  const d5=c.domainP5?`<div class="kv"><div><small>DOMAIN P@5 · SHAP (trung bình flow)</small><b>${vi(c.domainP5.shap,3)}</b></div><div><small>DOMAIN P@5 · LIME</small><b>${vi(c.domainP5.lime,3)}</b></div><div><small>JACCARD@5 SHAP–LIME</small><b>${c.agree?vi(c.agree.jaccard_5_mean,3):'—'}</b></div><div><small>ĐỒNG THUẬN DẤU@5</small><b>${c.agree&&c.agree.signed_agreement_5_mean!=null?pct(c.agree.signed_agreement_5_mean,0):'—'}</b></div></div>`:'';
  $('#attackDetail').innerHTML=`<div class="atk"><div class="card-label">${groupName[a.group]} · CỔNG ${a.port}</div><h2>${a.key}</h2><p class="lead">${a.summary}</p>
   <div class="legend">${badge('real')} ${badge('interactive')}</div>
   <div class="atk-tabs seg" id="atkTabs"><button class="on" data-t="scene">1 · Hoạt cảnh</button><button data-t="flow">2 · Dấu vết flow</button><button data-t="model">3 · Mô hình nói gì (số thật)</button><button data-t="blind">4 · Mô hình thấy / không thấy</button></div>
   <div data-pane="scene"><div class="scene-box"><canvas id="atkCv"></canvas><div class="scene-bar"><button class="btn sm lime" id="scPlay">⏸ Dừng</button><button class="btn sm alt" id="scReset">↺ Chạy lại</button><label class="toggle" style="color:#cfd8e6">Tốc độ <select id="scSpeed"><option value="0.5">0,5×</option><option value="1" selected>1×</option><option value="2">2×</option><option value="4">4×</option></select></label>${a.cfg.variants?`<label class="toggle" style="color:#cfd8e6">Kiểu <select id="scMode"><option value="header">slow headers</option><option value="body" selected>slow body</option><option value="read">slow read</option></select></label>`:''}${a.kind==='bot'?`<label class="toggle" style="color:#cfd8e6">Jitter <select id="scJit"><option value="0.03" selected>thấp (bot)</option><option value="0.4">cao (che giấu)</option></select></label>`:''}<span style="margin-left:auto;font-size:11px;color:#8e9ab0">${a.cfg.label}</span></div><div class="meters" id="atkMeters"></div><div class="scene-caption" id="atkCap"></div></div>
    <h4>Cách hoạt động</h4><ol>${a.how.map(x=>`<li>${x}</li>`).join('')}</ol></div>
   <div data-pane="flow" hidden><p class="note">Một flow đại diện (minh họa) của loại tấn công này, so với flow mở web bình thường. Thanh cam = tấn công, thanh xám = bình thường (thang log để thấy cả hai).</p>
    <div class="timeline" style="margin-bottom:12px"><svg id="atkTl" viewBox="0 0 900 140"></svg></div>
    <div class="cmp-head"><span>FEATURE</span><span>TẤN CÔNG</span><span>BÌNH THƯỜNG</span><span>GIÁ TRỊ</span></div>${cmp}
    <h4>Dấu hiệu ở mức flow</h4><p>${a.signals.map(s=>`<span class="tagpill">${s}</span>`).join('')}</p><div class="note">Số trên là từ flow minh họa tự sinh, chỉ để thấy <b>hình dạng</b> khác biệt. Số thật của mô hình nằm ở tab 3.</div></div>
   <div data-pane="model" hidden><div class="kv"><div><small>PRECISION</small><b>${pct(c.precision,2)}</b></div><div><small>RECALL</small><b>${pct(c.recall,2)}</b></div><div><small>F1</small><b>${pct(c.f1,2)}</b></div><div><small>FLOW TEST</small><b>${vi0(c.support)}</b></div></div>
    <p class="note ${l[1]==='bad'?'warn':''}"><b>${l[0]}.</b> ${a.careful}</p>
    <h4>Hay bị nhầm thành</h4><p>${conf.length?conf.map(([v,j])=>`<span class="tagpill miss">${esc(SHORT[P.classOrder[j]]||P.classOrder[j])}: ${vi0(v)} flow (${pct(v/tot,1)})</span>`).join(''):'Gần như không bị nhầm sang lớp khác.'}</p>
    <h4>SHAP toàn cục: feature đẩy điểm lớp này lên nhiều nhất</h4>${shapHtml}${ins}
    <h4>Đối chiếu tri thức miền</h4>${domHtml}${d5}
    <p style="margin-top:14px"><button class="btn sm" id="goCompare">Xem SHAP vs LIME trên một flow thật của lớp này →</button></p></div>
   <div data-pane="blind" hidden><div class="see-grid"><div><h4>✓ Mô hình thấy (78 flow feature)</h4><p>Cổng đích, thời lượng, số packet, tốc độ, IAT, kích thước packet, cờ TCP, cửa sổ TCP…</p><p>${a.signals.map(s=>`<span class="tagpill hit">${s}</span>`).join('')}</p></div>
     <div class="blind"><h4>✗ Mô hình KHÔNG thấy</h4><ul>${a.blind.map(b=>`<li>${b}</li>`).join('')}</ul></div></div>
    ${a.kind==='payload'?`<h4>Hai “ống kính” cùng một request</h4><div class="see-grid"><div><b>WAF / DPI đọc payload</b><div class="payload">${a.cfg.req}</div><small>${a.cfg.resp}</small></div><div><b>Flow-based IDS chỉ thấy</b><div class="payload"><span class="blur">${a.cfg.req.replace(/<[^>]+>/g,'')}</span></div><small>Port 80 · vài trăm byte · &lt; 1 s · cờ TCP bình thường</small></div></div>`:''}
    ${a.kind==='brute'?`<div class="note warn">Mật khẩu đang thử nằm trong payload được mã hóa hoặc ở tầng ứng dụng: flow-based IDS chỉ nhìn <b>nhịp kết nối</b>.</div>`:''}
    <h4>Cần thêm gì để chắc chắn?</h4><p>${a.extra}</p></div></div>`;
  const dlg=$('#attackDialog');if(!dlg.open)dlg.showModal();
  seg($('#atkTabs'),b=>{$$('#attackDetail [data-pane]').forEach(p=>p.hidden=p.dataset.pane!==b.dataset.t);if(b.dataset.t==='flow')drawTl(a)});
  startScene(a);
  $('#goCompare').onclick=()=>{dlg.close();HUB.focusCompare&&HUB.focusCompare(a.key);location.hash='#compare'};
  if(tab){const bt=$(`#atkTabs [data-t="${tab}"]`);bt&&bt.click()}
}
function drawTl(a){const pk=a.gen(),mx=Math.max(...pk.map(p=>p.t))||1;const X=t=>30+t/mx*840;let g=`<rect width="900" height="140" fill="#10182a" rx="10"/><line x1="30" x2="870" y1="70" y2="70" stroke="#3a4a66"/>`;
  pk.forEach(p=>{const up=p.dir==='f',h=6+Math.min(50,p.len/1400*50),col=p.flags.includes('R')?'#ff7c43':(up?'#29d3d1':'#b7f23d');g+=`<line x1="${X(p.t)}" x2="${X(p.t)}" y1="${up?70-h:70}" y2="${up?70:70+h}" stroke="${col}" stroke-width="3" stroke-linecap="round"/>`});
  g+=`<text x="30" y="16" fill="#29d3d1" font-size="10" font-family="DM Mono">FWD</text><text x="30" y="132" fill="#b7f23d" font-size="10" font-family="DM Mono">BWD</text><text x="870" y="132" fill="#8e9ab0" font-size="10" font-family="DM Mono" text-anchor="end">tổng thời gian ${vi(mx,mx<1?3:1)} s</text>`;$('#atkTl').innerHTML=g}
function startScene(a){cancelAnimationFrame(raf);const cv=$('#atkCv');scene=new Scene(cv,a);
  $('#scPlay').onclick=()=>{scene.playing=!scene.playing;$('#scPlay').textContent=scene.playing?'⏸ Dừng':'▶ Tiếp'};
  $('#scReset').onclick=()=>{const m=scene.mode;scene.reset();scene.mode=m};
  $('#scSpeed').onchange=e=>scene.speed=+e.target.value;
  const mo=$('#scMode');if(mo)mo.onchange=e=>{scene.mode=e.target.value;scene.reset();scene.mode=e.target.value};
  const jt=$('#scJit');if(jt)jt.onchange=e=>{a.cfg.jitter=+e.target.value;scene.reset()};
  lastTs=performance.now();const loop=ts=>{const dt=Math.min(.05,(ts-lastTs)/1000);lastTs=ts;if(!$('#attackDialog').open)return;scene.step(dt);scene.draw();
    $('#atkMeters').innerHTML=scene.meters().map(([l,v,t])=>`<div class="meter"><small>${l}</small><div class="m"><i style="width:${clamp(v,0,1)*100}%;${v>.9&&/CPU|chiếm|Băng/.test(l)?'background:#e5484d':''}"></i></div><output>${t}</output></div>`).join('');
    $('#atkCap').innerHTML=scene.caption();raf=requestAnimationFrame(loop)};raf=requestAnimationFrame(loop)}

HUB.reg(function attacksInit(){
  let group='all',term='';
  const render=()=>{const t=term.toLowerCase();const list=ATK.map((a,i)=>[a,i]).filter(([a])=>(group==='all'||a.group===group)&&(`${a.key} ${a.summary} ${a.signals.join(' ')} ${a.cfg.label}`.toLowerCase().includes(t)));
    $('#attackGrid').innerHTML=list.map(([a,i])=>cardHtml(a,i)).join('')||'<p>Không tìm thấy.</p>';$$('.attack-card').forEach(b=>b.onclick=()=>showAttack(+b.dataset.i))};
  seg($('#attackFilters'),b=>{group=b.dataset.group;render()});$('#attackSearch').oninput=e=>{term=e.target.value;render()};
  $('#closeDialog').onclick=()=>$('#attackDialog').close();$('#attackDialog').addEventListener('close',()=>cancelAnimationFrame(raf));
  $('#attackDialog').addEventListener('click',e=>{if(e.target===$('#attackDialog'))$('#attackDialog').close()});
  render();
});
})();
