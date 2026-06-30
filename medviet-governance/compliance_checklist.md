# Checklist tuân thủ NĐ13/2023 — MedViet AI Platform

## A. Lưu trữ dữ liệu trong nước

- [x] Toàn bộ dữ liệu bệnh nhân lưu trên máy chủ đặt tại Việt Nam
- [x] Backup chạy sang zone dự phòng cũng trong lãnh thổ VN
- [x] Mọi luồng data ra ngoài biên giới đều được ghi log kèm lý do

## B. Thu thập và quản lý đồng ý

- [x] Bệnh nhân ký đồng ý trước khi dữ liệu được dùng để huấn luyện mô hình
- [x] Bệnh nhân có thể rút đồng ý bất kỳ lúc nào qua `DELETE /api/patients/{id}`
- [x] Mỗi bản đồng ý lưu kèm timestamp và phiên bản biểu mẫu

## C. Thông báo vi phạm trong 72 giờ

- [x] Quy trình xử lý sự cố đã được soạn thảo và phân công người phụ trách
- [x] Hệ thống cảnh báo tự động kích hoạt khi phát hiện breach (Prometheus alerting)
- [x] Báo cáo vi phạm gửi Bộ Thông tin và Truyền thông trong vòng 72 giờ theo Điều 23 NĐ13

## D. Bổ nhiệm Data Protection Officer

- [x] DPO đã được bổ nhiệm chính thức
- [x] Liên hệ: dpo@medviet.vn

## E. Biện pháp kỹ thuật (mapping sang yêu cầu NĐ13)

| Yêu cầu NĐ13 | Biện pháp kỹ thuật | Trạng thái | Phụ trách |
|---|---|---|---|
| Tối thiểu hóa dữ liệu | Anonymization pipeline dùng Microsoft Presidio, detection rate >= 95% | Hoàn thành | AI Team |
| Kiểm soát truy cập | RBAC qua Casbin (policy.csv + model.conf) kết hợp ABAC qua OPA (opa_policy.rego) | Hoàn thành | Platform Team |
| Mã hóa | AES-256-GCM envelope encryption (SimpleVault) cho data at rest; TLS 1.3 in transit | Hoàn thành | Infra Team |
| Audit log | FastAPI middleware ghi log từng request (user, endpoint, timestamp, IP) ra JSON, rotate daily | Hoàn thành | Platform Team |
| Phát hiện xâm phạm | Prometheus + Grafana alert khi rate 4xx tăng bất thường; Falco theo dõi truy cập file trái phép | Hoàn thành | Security Team |

## F. Hướng dẫn kỹ thuật

### Audit logging

FastAPI middleware ghi mỗi request thành một dòng JSON:

```python
@app.middleware("http")
async def audit_log(request, call_next):
    response = await call_next(request)
    logger.info(json.dumps({
        "timestamp": datetime.utcnow().isoformat(),
        "user": request.headers.get("Authorization", "anon"),
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ip": request.client.host,
    }))
    return response
```

Log ghi vào `logs/audit.jsonl` (local) và ship lên CloudWatch Logs (production). Retention tối thiểu 365 ngày theo NĐ13.

### Phát hiện xâm phạm

Prometheus scrape `/metrics` được expose từ FastAPI qua `prometheus-fastapi-instrumentator`. Hai alert rule chính:

- `rate(http_requests_total{status=~"4.."}[5m]) > 10` kích hoạt PagerDuty
- Volume export tăng đột biến gửi email DPO trong 1 giờ, báo Bộ TTTT trong 72 giờ theo Điều 23

Falco chạy song song trên host để phát hiện truy cập file trái phép ngoài luồng API.
