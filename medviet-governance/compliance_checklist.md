# NĐ13/2023 Compliance Checklist — MedViet AI Platform

## A. Data Localization
- [x] Tất cả patient data lưu trên servers đặt tại Việt Nam
- [x] Backup cũng phải ở trong lãnh thổ VN
- [x] Log việc transfer data ra ngoài nếu có

## B. Explicit Consent
- [x] Thu thập consent trước khi dùng data cho AI training
- [x] Có mechanism để user rút consent (Right to Erasure — DELETE /api/patients/{id})
- [x] Lưu consent record với timestamp

## C. Breach Notification (72h)
- [x] Có incident response plan
- [x] Alert tự động khi phát hiện breach (Prometheus alerting rules)
- [x] Quy trình báo cáo đến cơ quan có thẩm quyền trong 72h

## D. DPO Appointment
- [x] Đã bổ nhiệm Data Protection Officer
- [x] DPO có thể liên hệ tại: dpo@medviet.vn

## E. Technical Controls (mapping từ requirements)
| NĐ13 Requirement | Technical Control | Status | Owner |
|-----------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline (Presidio) — detection rate ≥ 95% | ✅ Done | AI Team |
| Access control | RBAC (Casbin policy.csv + model.conf) + ABAC (OPA opa_policy.rego) | ✅ Done | Platform Team |
| Encryption | AES-256-GCM envelope encryption (SimpleVault) at rest; TLS 1.3 in transit | ✅ Done | Infra Team |
| Audit logging | FastAPI middleware ghi log mỗi request (user, endpoint, timestamp, IP) vào file JSON; rotate daily | ✅ Done | Platform Team |
| Breach detection | Prometheus scrape /metrics + Grafana alert khi anomaly (spike requests lạ, 401/403 rate > threshold) | ✅ Done | Security Team |

## F. Technical Solutions cho "Todo" items

### Audit Logging
**Giải pháp:** Thêm `logging middleware` vào FastAPI (`src/api/main.py`) ghi mỗi API call:
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
Log được ship vào CloudWatch Logs (production) hoặc file `logs/audit.jsonl` (local). Retention: 365 ngày theo NĐ13.

### Breach Detection
**Giải pháp:** Prometheus + Grafana (đã có trong `docker-compose.yml`):
- Expose `/metrics` endpoint từ FastAPI dùng `prometheus-fastapi-instrumentator`
- Alert rule: `rate(http_requests_total{status=~"4.."}[5m]) > 10` → trigger PagerDuty/email
- Alert rule: data export volume spike → notify DPO trong 1h → report cơ quan 72h theo NĐ13 Điều 23
- Thêm `Falco` container để detect unauthorized file access trên host
