# Hướng dẫn thu thêm dữ liệu lab (tấn công và Benign)

Mục đích: đủ lượt độc lập cho mỗi loại để chia train, validation, test theo lượt, và có Benign trong cùng môi trường Kali, Ubuntu để đo báo nhầm. Lệnh cài đặt, hàm `run_lab` và cấu hình công cụ lấy từ sổ tay trong `Java_CICFlowMeter_M0_Trial/README.md` (mục "SỔ TAY CHẠY LẠI CÁC LƯỢT LAB").

## 1. Quy tắc chung (đọc trước)

1. **Mỗi lượt một file PCAP, chỉ một loại traffic.** Không chạy tấn công và Benign cùng lúc. Script gán nhãn theo cặp IP và cổng, nên traffic lẫn vào sẽ bị gán sai nhãn.
2. **Lệnh `curl` kiểm tra server phải chạy ngoài lúc đang bắt gói** (trước khi bấm Start hoặc sau khi bấm Stop trong Wireshark). Nếu không, các request đó sẽ bị gán nhãn tấn công.
3. Nghỉ ít nhất 60 giây giữa hai lượt để kết nối cũ đóng hết.
4. Không đổi cấu hình Apache, SSH hay tắt timeout để ép model nhận đúng.
5. Ghi mỗi lượt một dòng vào `manifests/new_runs_template.csv` ngay sau khi chạy.
6. Kiểm tra IP mỗi lần mở máy bằng `ip -br addr`. Hướng dẫn dùng Kali 192.168.11.133, Ubuntu 192.168.11.134. Nếu IP đổi thì sửa lệnh và ghi vào manifest.

## 2. Bắt gói trên Windows

Chỉ cần Wireshark, không cần dashboard. Dữ liệu train được trích lại offline từ PCAP.

1. Mở Wireshark, chọn card **VMware Virtual Ethernet Adapter for VMnet1**.
2. Không đặt capture filter. Có thể đặt display filter để xem: `ip.addr == 192.168.11.133 && ip.addr == 192.168.11.134`.
3. Bấm Start, đợi 5 giây, rồi mới chạy lệnh trên Kali.
4. Công cụ dừng xong, đợi thêm 10 giây rồi bấm Stop.
5. File > Save As > định dạng **pcapng**, đặt tên theo bảng ở mục 5, lưu vào `C:\Users\LOQ\Downloads\SELF_KLTN\M0_Lab_Adaptation_Trial\pcaps_new\`.

Nếu muốn dùng dòng lệnh: `"C:\Program Files\Wireshark\dumpcap.exe" -D` để xem số thứ tự card, rồi `"C:\Program Files\Wireshark\dumpcap.exe" -i <số card VMnet1> -w <tên file>.pcapng`, dừng bằng Ctrl+C.

## 3. Chuẩn bị Ubuntu (một lần)

Tạo trang web và file có nhiều kích thước để Benign giống duyệt web thật:

```bash
sudo mkdir -p /var/www/html/docs /var/www/html/files
for i in $(seq 1 10); do
  printf '<html><head><title>Trang %s</title></head><body><h1>Trang %s</h1><p>%s</p><a href="p%s.html">tiếp</a></body></html>\n' \
    "$i" "$i" "$(head -c $((i*3000)) /dev/urandom | base64 -w0)" "$(( i % 10 + 1 ))" | sudo tee /var/www/html/docs/p$i.html > /dev/null
done
sudo dd if=/dev/urandom of=/var/www/html/files/f10k.bin bs=1K count=10 status=none
sudo dd if=/dev/urandom of=/var/www/html/files/f200k.bin bs=1K count=200 status=none
sudo dd if=/dev/urandom of=/var/www/html/files/f2m.bin bs=1M count=2 status=none
curl -sI http://192.168.11.134/docs/p1.html | head -1
```

Kiểm tra dịch vụ trước mỗi buổi: `systemctl is-active ssh apache2`.

## 4. Chuẩn bị Kali (mỗi lần mở terminal)

Dán hàm `run_lab` ở mục 3 của sổ tay. Tạo danh sách mật khẩu sai cho SSH (một lần):

```bash
cd ~/ids-demo
for i in $(seq 1 200); do printf 'WrongLabPass%03d\n' "$i"; done > passwords200.txt
```

Cho Benign SSH tự động, tạo khóa đăng nhập (một lần):

```bash
ssh-keygen -t ed25519 -N '' -f ~/.ssh/lab_benign
ssh-copy-id -i ~/.ssh/lab_benign.pub ids_demo@192.168.11.134
```

## 5. Danh sách lượt cần thu

Mỗi loại cần ít nhất ba lượt: một cho train, một cho validation (chọn trọng số), một cho test. Lượt cũ vẫn dùng được.

| Mã lượt | Loại | Lệnh trên Kali | Thời lượng | Tên file PCAP |
|---|---|---|---|---|
| ssh_hydra_2 | SSH | `run_lab ssh-hydra-200 300 hydra -l ids_demo -P passwords200.txt -t 4 -V 192.168.11.134 ssh` | tới 300 s | `ssh-hydra-200-<ngày giờ>.pcapng` |
| ssh_hydra_3 | SSH | như trên, chạy lại sau 2 phút | tới 300 s | `ssh-hydra-200b-<ngày giờ>.pcapng` |
| ssh_patator_2 | SSH | `run_lab ssh-patator-200 300 patator ssh_login host=192.168.11.134 port=22 user=ids_demo password=FILE0 0=passwords200.txt -t 4 --max-retries 0 --timeout 10` | tới 300 s | `ssh-patator-200-<ngày giờ>.pcapng` |
| slowloris_3 | Slowloris | `cd ~/ids-demo/slowloris && run_lab slowloris-50s 180 python3 -u slowloris.py 192.168.11.134 -p 80 -s 50 --sleeptime 10 -v` | 180 s | `slowloris-50-180s-<ngày giờ>.pcapng` |
| slowloris_4 | Slowloris | như trên, chạy lại | 180 s | `slowloris-50b-180s-<ngày giờ>.pcapng` |
| loic_http_2 | LOIC-HTTP | Mở LOIC như sổ tay mục 8; HTTP, cổng 80, subsite `/`, Threads=5, Sockets/Thread=25, giữ vị trí thanh tốc độ như lượt trước; bấm Stop flooding sau 120 s | 120 s | `loic-http-t5s25-120s-<ngày giờ>.pcapng` |
| loic_http_3 | LOIC-HTTP | như trên | 120 s | `loic-http-t5s25b-120s-<ngày giờ>.pcapng` |
| goldeneye_3 | GoldenEye | `cd ~/ids-demo/GoldenEye && run_lab goldeneye-level1-30s 30 python3 -u goldeneye.py http://192.168.11.134/ -w 1 -s 2 -m get` | 30 s | `goldeneye-level1-30s-<ngày giờ>.pcapng` |
| hulkgo_3 | Hulk-Go | `cd ~/ids-demo/hulk-go && run_lab hulk-go-level1-30s 30 env HULKMAXPROCS=3 ./hulk-lab -site http://192.168.11.134/` | 30 s | `hulk-go-level1-30s-<ngày giờ>.pcapng` |

Ghi chú:
- Hydra và Patator với 200 mật khẩu và 4 luồng tạo nhiều kết nối hơn lượt cũ (lượt cũ chỉ ra 5 và 4 flow). Không dùng `-f` để công cụ thử hết danh sách. Nếu Ubuntu chặn vì quá nhiều kết nối, ghi lại trong cột ghi chú, không tắt bảo vệ.
- Slowloris giữ kết nối lâu, nên cần nhiều socket và thời gian dài hơn mới đủ flow.
- LOIC: chụp ảnh màn hình cấu hình trước khi bấm bắt đầu, lưu cùng tên với PCAP.

## 6. Benign trong lab

Cùng máy Kali gửi tới cùng Ubuntu, để kiểm tra model có báo nhầm vì đặc điểm môi trường (cửa sổ TCP của Kali, cổng 80 và 22) hay không. Thu ít nhất ba lượt, mỗi lượt khoảng 20 phút.

**benign_web_script** (tự động, khoảng 1.000 kết nối):

```bash
run_lab benign-web-curl 1200 bash -c '
pages=(/ /docs/p1.html /docs/p2.html /docs/p3.html /docs/p5.html /docs/p8.html /files/f10k.bin /files/f200k.bin /files/f2m.bin)
while true; do
  curl -s -o /dev/null "http://192.168.11.134${pages[RANDOM % ${#pages[@]}]}"
  sleep "$(( RANDOM % 3 )).$(( RANDOM % 10 ))"
done'
```

**benign_web_browser** (thủ công, 20 phút): mở Firefox trên Kali, vào `http://192.168.11.134/docs/p1.html`, bấm qua các trang, tải vài file trong `/files/`, tải lại trang, đóng mở tab. Lượt này có kết nối giữ lâu và nhiều request trên một kết nối, giống người dùng thật.

**benign_ssh** (20 phút, gồm đăng nhập đúng và chép file):

```bash
run_lab benign-ssh 1200 bash -c '
while true; do
  ssh -i ~/.ssh/lab_benign -o BatchMode=yes ids_demo@192.168.11.134 "uptime; ls -la; df -h; sleep $(( RANDOM % 20 + 5 ))"
  scp -q -i ~/.ssh/lab_benign ids_demo@192.168.11.134:/etc/os-release /tmp/os-release
  sleep $(( RANDOM % 15 + 5 ))
done'
```

Thêm vài lần đăng nhập bằng mật khẩu đúng gõ tay (`ssh ids_demo@192.168.11.134`, chạy vài lệnh, `exit`) trong cùng lượt, ghi số lần vào ghi chú.

Benign chỉ dùng cho validation và test ở đợt đầu, không đưa vào train cho đến khi có quyết định riêng.

## 7. Sau mỗi lượt

1. Ubuntu lưu log (lệnh ở sổ tay mục 9): Apache access và error, `journalctl -u ssh`.
2. Kali giữ file trong `~/ids-demo/logs/` do `run_lab` tạo.
3. Chép PCAP, log Kali, log Ubuntu và ảnh LOIC vào `M0_Lab_Adaptation_Trial/pcaps_new/<mã lượt>/`.
4. Điền một dòng vào `manifests/new_runs_template.csv`.
5. Sau đó chạy `curl -o /dev/null -sS -w 'HTTP=%{http_code} time=%{time_total}s\n' http://192.168.11.134/` (ngoài lúc bắt gói) để ghi server còn phản hồi hay không.

## 8. Sau khi thu xong

Báo lại danh sách mã lượt. Các bước tiếp theo: tính mã băm, trích bằng cùng bản Java profile M0, kiểm đối soát packet (script 02), gán nhãn, chốt chia train, validation, test theo lượt trước khi train, chọn trọng số lab trên validation, chạy lại v2 và đo báo nhầm trên Benign lab.
